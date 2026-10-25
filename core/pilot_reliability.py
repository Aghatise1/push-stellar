"""Read-only pilot reliability diagnostics for Push staff and release checks."""
from datetime import timedelta

from django.conf import settings
from django.db.models import Count, Q
from django.urls import reverse
from django.utils import timezone

from .models import EscrowAgreement, EscrowTransaction

DEFAULT_STALE_MINUTES = 15

EXPECTED_CHAIN_STATES = {
    'awaiting_acceptance': frozenset({'Unfunded'}),
    'awaiting_funding': frozenset({'Unfunded'}),
    'funded': frozenset({'Funded'}),
    'submitted': frozenset({'Submitted'}),
    'disputed': frozenset({'Disputed'}),
    'paid': frozenset({'Released', 'Resolved'}),
    'cancelled': frozenset({'Refunded', 'Unfunded'}),
}

KNOWN_CHAIN_STATES = frozenset({
    'Unfunded',
    'Funded',
    'Submitted',
    'Disputed',
    'Released',
    'Resolved',
    'Refunded',
})

STANDARD_TRANSACTION_STATES = ('prepared', 'pending', 'confirmed', 'failed', 'expired')


def stale_minutes() -> int:
    raw = getattr(settings, 'PUSH_PILOT_STALE_MINUTES', DEFAULT_STALE_MINUTES)
    if isinstance(raw, bool):
        return DEFAULT_STALE_MINUTES
    try:
        value = int(str(raw).strip())
    except (TypeError, ValueError):
        return DEFAULT_STALE_MINUTES
    return value if value > 0 else DEFAULT_STALE_MINUTES


def abbreviate_address(value: str) -> str:
    text = str(value or '').strip()
    if not text:
        return ''
    if len(text) > 10:
        return f'{text[:6]}…{text[-4:]}'
    if len(text) > 2:
        return f'{text[:2]}…'
    return '…'


def expected_chain_states(assignment_status: str) -> set[str]:
    status = str(assignment_status or '').strip()
    return set(EXPECTED_CHAIN_STATES.get(status, frozenset()))


def _age_seconds(now, timestamp) -> int:
    if not timestamp:
        return 0
    return max(0, int((now - timestamp).total_seconds()))


def build_pilot_reliability_report(*, now=None, attention_limit: int = 100) -> dict:
    current_time = now or timezone.now()
    threshold_minutes = stale_minutes()
    stale_cutoff = current_time - timedelta(minutes=threshold_minutes)
    limit = max(0, int(attention_limit)) if isinstance(attention_limit, int) else 100

    configured_contract = (
        settings.PUSH_TESTNET_ESCROW_STAFF_CONTRACT
        if settings.PUSH_TESTNET_ONLY
        else settings.PUSH_TESTNET_ESCROW_CONTRACT
    )
    deployment = {
        'tier': str(getattr(settings, 'PUSH_DEPLOYMENT_TIER', 'development') or 'development'),
        'release': str(getattr(settings, 'PUSH_RELEASE', '') or 'unreported'),
        'network': 'stellar-testnet',
        'testnet_only': bool(getattr(settings, 'PUSH_TESTNET_ONLY', True)),
        'escrow_enabled': bool(getattr(settings, 'PUSH_TESTNET_ESCROW_ENABLED', False) and configured_contract),
    }

    by_assignment_status = {status: 0 for status in EXPECTED_CHAIN_STATES}
    by_chain_status = {status: 0 for status in KNOWN_CHAIN_STATES}
    by_pair = {}
    agreement_total = 0

    for row in (
        EscrowAgreement.objects.values('assignment__status', 'chain_status')
        .annotate(count=Count('pk'))
        .order_by('assignment__status', 'chain_status')
    ):
        a_status = str(row['assignment__status'] or '')
        c_status = str(row['chain_status'] or '')
        count = int(row['count'])
        agreement_total += count
        by_assignment_status[a_status] = by_assignment_status.get(a_status, 0) + count
        by_chain_status[c_status] = by_chain_status.get(c_status, 0) + count
        by_pair[f'{a_status}:{c_status}'] = count

    transaction_counts = {'total': 0}
    for state in STANDARD_TRANSACTION_STATES:
        transaction_counts[state] = 0
    for row in EscrowTransaction.objects.values('state').annotate(count=Count('pk')).order_by('state'):
        state = str(row['state'] or '')
        count = int(row['count'])
        transaction_counts['total'] += count
        transaction_counts[state] = transaction_counts.get(state, 0) + count

    attention_items = []

    agreements = (
        EscrowAgreement.objects.select_related('assignment')
        .only(
            'id',
            'assignment_id',
            'client_address',
            'asset',
            'amount',
            'chain_status',
            'accepted_at',
            'assignment__id',
            'assignment__status',
            'assignment__created_at',
        )
        .order_by('id')
    )
    for agreement in agreements:
        a_status = str(agreement.assignment.status or '')
        c_status = str(agreement.chain_status or '')
        expected = EXPECTED_CHAIN_STATES.get(a_status)
        if expected is None or c_status not in KNOWN_CHAIN_STATES:
            action = 'unknown_state'
            safe_state = f'unknown_state:{a_status}:{c_status}'
        elif c_status not in expected:
            action = 'state_mismatch'
            safe_state = f'mismatch:{a_status}:{c_status}'
        else:
            continue

        reference_time = agreement.accepted_at or agreement.assignment.created_at
        attention_items.append({
            'assignment_id': str(agreement.assignment_id),
            'action': action,
            'state': safe_state,
            'age_seconds': _age_seconds(current_time, reference_time),
            'asset': str(agreement.asset),
            'amount': int(agreement.amount),
            'source': abbreviate_address(agreement.client_address),
            'workroom_url': reverse('escrow_detail', args=[agreement.assignment_id]),
        })

    attention_tx_filter = (
        Q(state__in=['prepared', 'pending'], created_at__lte=stale_cutoff)
        | Q(state='failed')
        | ~Q(state__in=STANDARD_TRANSACTION_STATES)
    )
    attention_txs = (
        EscrowTransaction.objects.filter(attention_tx_filter)
        .select_related('escrow')
        .only(
            'id',
            'action',
            'source',
            'state',
            'created_at',
            'escrow__id',
            'escrow__assignment_id',
            'escrow__asset',
            'escrow__amount',
        )
        .order_by('created_at', 'id')
    )
    for tx in attention_txs:
        if tx.state in ('prepared', 'pending'):
            safe_state = f'stale_{tx.state}'
        elif tx.state == 'failed':
            safe_state = 'failed'
        else:
            safe_state = f'unknown_state:{tx.state}'

        attention_items.append({
            'assignment_id': str(tx.escrow.assignment_id),
            'action': str(tx.action),
            'state': safe_state,
            'age_seconds': _age_seconds(current_time, tx.created_at),
            'asset': str(tx.escrow.asset),
            'amount': int(tx.escrow.amount),
            'source': abbreviate_address(tx.source),
            'workroom_url': reverse('escrow_detail', args=[tx.escrow.assignment_id]),
        })

    return {
        'generated_at': current_time,
        'stale_minutes': threshold_minutes,
        'deployment': deployment,
        'agreement_counts': {
            'total': agreement_total,
            'by_assignment_status': by_assignment_status,
            'by_chain_status': by_chain_status,
            'by_pair': by_pair,
        },
        'transaction_counts': transaction_counts,
        'attention': attention_items[:limit],
        'attention_total': len(attention_items),
    }
