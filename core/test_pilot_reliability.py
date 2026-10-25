import hashlib
from datetime import datetime, timedelta, timezone as dt_timezone
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from stellar_sdk import Keypair

from core.models import Assignment, EscrowAgreement, EscrowTransaction, Job, StaffAccess, User
from core.pilot_reliability import (
    abbreviate_address,
    build_pilot_reliability_report,
    expected_chain_states,
    stale_minutes,
)


class PilotReliabilityHelperTests(SimpleTestCase):
    def test_stale_minutes_defaults_and_rejects_invalid_values(self):
        self.assertEqual(stale_minutes(), 15)
        for invalid in (None, '', 'abc', 0, -5, '0', '-10', [], {}, True, False):
            with self.subTest(invalid=invalid):
                with override_settings(PUSH_PILOT_STALE_MINUTES=invalid):
                    self.assertEqual(stale_minutes(), 15)
        for valid, expected in ((5, 5), ('20', 20), (1, 1)):
            with self.subTest(valid=valid):
                with override_settings(PUSH_PILOT_STALE_MINUTES=valid):
                    self.assertEqual(stale_minutes(), expected)

    def test_abbreviate_address_never_returns_the_full_value(self):
        self.assertEqual(abbreviate_address(''), '')
        self.assertEqual(abbreviate_address('   '), '')
        self.assertEqual(abbreviate_address(None), '')
        full_address = 'GBBD47IF6LWK7P7MDEVSCWR7DPUWV3NY3DTQEVFL4NAT4AQH3ZLLFLA5'
        short = abbreviate_address(full_address)
        self.assertTrue(short)
        self.assertNotEqual(short, full_address)
        self.assertNotIn(full_address, short)
        self.assertTrue(short.startswith('GBBD47'))
        self.assertTrue(short.endswith('FLA5'))
        short_input = 'GSHORT1234'
        abbreviated_short = abbreviate_address(short_input)
        self.assertNotEqual(abbreviated_short, short_input)

    def test_expected_chain_states_matches_spec_rules(self):
        self.assertEqual(expected_chain_states('awaiting_funding'), {'Unfunded'})
        self.assertEqual(expected_chain_states('funded'), {'Funded'})
        self.assertEqual(expected_chain_states('submitted'), {'Submitted'})
        self.assertEqual(expected_chain_states('disputed'), {'Disputed'})
        self.assertEqual(expected_chain_states('paid'), {'Released', 'Resolved'})
        self.assertEqual(expected_chain_states('cancelled'), {'Refunded', 'Unfunded'})
        self.assertEqual(expected_chain_states('unknown_status'), set())


class PilotReliabilityReportTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.fixed_now = datetime(2026, 10, 25, 12, 0, 0, tzinfo=dt_timezone.utc)
        accepted = cls.fixed_now - timedelta(days=2)
        cls.client_address = Keypair.random().public_key
        cls.worker_address = Keypair.random().public_key
        cls.reviewer_address = Keypair.random().public_key
        cls.owner_user = User.objects.create_user(
            username='owner@example.test',
            email='owner@example.test',
            password='Independent-cobalt-732!',
            display_name='Owner User',
            email_verified=True,
            stellar_address=cls.reviewer_address,
            terms_version='2026-10-06.1',
            terms_accepted_at=accepted,
        )
        StaffAccess.objects.create(user=cls.owner_user, role='owner', status='approved', approved_at=accepted)
        cls.client_user = User.objects.create_user(
            username='client@example.test',
            email='client@example.test',
            password='Independent-cobalt-732!',
            display_name='Client User',
            email_verified=True,
            stellar_address=cls.client_address,
            terms_version='2026-10-06.1',
            terms_accepted_at=accepted,
        )
        cls.worker_user = User.objects.create_user(
            username='worker@example.test',
            email='worker@example.test',
            password='Independent-cobalt-732!',
            display_name='Worker User',
            email_verified=True,
            stellar_address=cls.worker_address,
            terms_version='2026-10-06.1',
            terms_accepted_at=accepted,
        )
        cls.counter = 0

    def make_agreement(self, assignment_status, chain_status, *, amount=125, asset='USDC', accepted_delta_seconds=3600):
        type(self).counter += 1
        idx = type(self).counter
        job = Job.objects.create(
            owner=self.client_user,
            project=f'Project {idx}',
            title=f'Job {idx}',
            description='Private job description',
            deliverables='Deliverable spec',
            category='Development',
            budget=amount,
            payment_asset=asset,
            deadline=self.fixed_now.date() + timedelta(days=7),
            moderation_status='approved',
            status='assigned',
        )
        assignment = Assignment.objects.create(
            job=job,
            worker=self.worker_user,
            scope='Private scope details',
            budget=amount,
            status=assignment_status,
            escrow_required=True,
            accepted_terms_at=self.fixed_now - timedelta(seconds=accepted_delta_seconds),
        )
        agreement = EscrowAgreement.objects.create(
            staff_governed=True,
            assignment=assignment,
            reviewer=self.owner_user,
            contract='CCONTRACT1234567890123456789012345678901234567890123456',
            agreement_id=hashlib.sha256(f'agreement-{idx}'.encode()).hexdigest(),
            client_address=self.client_address,
            worker_address=self.worker_address,
            reviewer_address=self.reviewer_address,
            asset=asset,
            token_address='CTOKEN1234567890123456789012345678901234567890123456789',
            amount=amount,
            deadline=int((self.fixed_now + timedelta(days=7)).timestamp()),
            review_seconds=86400,
            revision_limit=2,
            chain_status=chain_status,
            accepted_at=self.fixed_now - timedelta(seconds=accepted_delta_seconds),
        )
        return agreement

    def make_tx(self, agreement, *, action='fund', state='prepared', age_seconds=60, source=None):
        type(self).counter += 1
        idx = type(self).counter
        tx = EscrowTransaction.objects.create(
            escrow=agreement,
            actor=self.client_user,
            action=action,
            source=source or self.client_address,
            prepared_xdr=f'SECRET_PREPARED_XDR_{idx}',
            signed_xdr=f'SECRET_SIGNED_XDR_{idx}',
            tx_hash=hashlib.sha256(f'tx-{idx}'.encode()).hexdigest(),
            state=state,
        )
        created_at = self.fixed_now - timedelta(seconds=age_seconds)
        EscrowTransaction.objects.filter(pk=tx.pk).update(created_at=created_at)
        tx.refresh_from_db()
        return tx

    def test_report_aggregates_all_defined_pairs_mismatches_thresholds_and_bounds(self):
        # All 8 valid defined pairs (including agreement with no transactions)
        a_unfunded = self.make_agreement('awaiting_funding', 'Unfunded', amount=50, asset='XLM')
        a_funded = self.make_agreement('funded', 'Funded', amount=100, asset='USDC')
        a_submitted = self.make_agreement('submitted', 'Submitted', amount=150, asset='USDC')
        a_disputed = self.make_agreement('disputed', 'Disputed', amount=200, asset='XLM')
        a_paid_released = self.make_agreement('paid', 'Released', amount=250, asset='USDC')
        a_paid_resolved = self.make_agreement('paid', 'Resolved', amount=300, asset='USDC')
        a_cancelled_refunded = self.make_agreement('cancelled', 'Refunded', amount=350, asset='XLM')
        a_cancelled_unfunded = self.make_agreement('cancelled', 'Unfunded', amount=400, asset='XLM')  # no transactions

        # High-confidence mismatch
        a_mismatch = self.make_agreement('funded', 'Unfunded', amount=500, asset='USDC', accepted_delta_seconds=1200)
        # Unknown state combination
        a_unknown = self.make_agreement('unexpected_local', 'UnexpectedChain', amount=600, asset='XLM', accepted_delta_seconds=1800)

        # Transactions covering threshold and terminal states
        self.make_tx(a_unfunded, action='fund', state='prepared', age_seconds=14 * 60 + 59)  # younger than 15m -> ok
        tx_at_threshold = self.make_tx(a_funded, action='fund', state='prepared', age_seconds=15 * 60)  # exactly 15m -> attention
        tx_old_pending = self.make_tx(a_submitted, action='submit', state='pending', age_seconds=20 * 60)  # older pending -> attention
        tx_failed = self.make_tx(a_disputed, action='open_dispute', state='failed', age_seconds=120)  # failed -> attention
        self.make_tx(a_paid_released, action='approve', state='confirmed', age_seconds=3600)  # confirmed -> ok
        self.make_tx(a_paid_resolved, action='resolve', state='expired', age_seconds=7200)  # expired -> counted, not attention

        report = build_pilot_reliability_report(now=self.fixed_now)
        self.assertEqual(report['generated_at'], self.fixed_now)
        self.assertEqual(report['stale_minutes'], 15)
        self.assertIn('tier', report['deployment'])
        self.assertIn('escrow_enabled', report['deployment'])

        # Agreement counts include the transaction-less agreement and all 10 agreements
        self.assertEqual(report['agreement_counts']['total'], 10)
        self.assertEqual(report['agreement_counts']['by_assignment_status']['paid'], 2)
        self.assertEqual(report['agreement_counts']['by_assignment_status']['cancelled'], 2)
        self.assertEqual(report['agreement_counts']['by_assignment_status']['funded'], 2)
        self.assertEqual(report['agreement_counts']['by_chain_status']['Unfunded'], 3)

        # Transaction counts
        self.assertEqual(
            report['transaction_counts'],
            {
                'total': 6,
                'prepared': 2,
                'pending': 1,
                'confirmed': 1,
                'failed': 1,
                'expired': 1,
            },
        )

        # Attention items: 1 mismatch + 1 unknown + 1 at threshold + 1 older pending + 1 failed = 5
        self.assertEqual(report['attention_total'], 5)
        self.assertEqual(len(report['attention']), 5)

        allowed_keys = {'assignment_id', 'action', 'state', 'age_seconds', 'asset', 'amount', 'source', 'workroom_url'}
        serialized = str(report)
        self.assertNotIn('SECRET_PREPARED_XDR', serialized)
        self.assertNotIn('SECRET_SIGNED_XDR', serialized)
        self.assertNotIn(self.client_address, serialized)
        self.assertNotIn(self.worker_address, serialized)
        self.assertNotIn(self.reviewer_address, serialized)
        self.assertNotIn('Private scope details', serialized)
        self.assertNotIn('Private job description', serialized)

        for item in report['attention']:
            self.assertEqual(set(item.keys()), allowed_keys)
            self.assertEqual(item['workroom_url'], reverse('escrow_detail', args=[item['assignment_id']]))
            self.assertEqual(item['source'], abbreviate_address(self.client_address))

        attention_by_assignment = {(item['assignment_id'], item['action']): item for item in report['attention']}
        self.assertIn((str(a_mismatch.assignment_id), 'state_mismatch'), attention_by_assignment)
        self.assertIn((str(a_unknown.assignment_id), 'unknown_state'), attention_by_assignment)
        self.assertEqual(
            attention_by_assignment[(str(tx_at_threshold.escrow.assignment_id), 'fund')]['age_seconds'],
            900,
        )
        self.assertEqual(
            attention_by_assignment[(str(tx_old_pending.escrow.assignment_id), 'submit')]['age_seconds'],
            1200,
        )
        self.assertEqual(
            attention_by_assignment[(str(tx_failed.escrow.assignment_id), 'open_dispute')]['state'],
            'failed',
        )

        # Bounded attention list preserves attention_total and complete counts
        bounded = build_pilot_reliability_report(now=self.fixed_now, attention_limit=2)
        self.assertEqual(bounded['attention_total'], 5)
        self.assertEqual(len(bounded['attention']), 2)
        self.assertEqual(bounded['agreement_counts']['total'], 10)
        self.assertEqual(bounded['transaction_counts']['total'], 6)
