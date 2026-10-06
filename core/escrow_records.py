"""Idempotent application records from verified testnet contract state; no broadcasting."""
from datetime import datetime, timezone as dt_timezone
from django.db import transaction
from django.utils import timezone
from stellar_sdk.soroban_rpc import GetTransactionStatus
from stellar_sdk import TransactionEnvelope
from . import escrow as chain
from .models import Assignment,EscrowAgreement,EscrowTransaction,Submission,Payment,Event,Dispute,Job
from .stellar import StellarVerificationError


def apply_confirmed(record,rpc):
    ledger=chain.read_agreement(record.escrow,rpc)
    with transaction.atomic():
        record=EscrowTransaction.objects.select_for_update().select_related('escrow__assignment__job','actor').get(pk=record.pk)
        if record.state=='confirmed':return
        agreement=EscrowAgreement.objects.select_for_update().get(pk=record.escrow_id)
        item=Assignment.objects.select_for_update().get(pk=agreement.assignment_id)
        action=record.action
        status=ledger['status'][0]
        expected={'fund':'Funded','submit':'Submitted','approve':'Released','revise':'Funded','dispute':'Disputed','refund_expired':'Refunded','claim_expired':'Released','resolve':'Resolved'}[action]
        if status!=expected:
            raise StellarVerificationError('The ledger advanced outside this workflow. Staff must reconcile the record before further transactions.')
        agreement.chain_status=status
        agreement.deadline=ledger['deadline'];agreement.review_until=ledger['review_until']
        item.status={'Funded':'funded','Submitted':'submitted','Disputed':'disputed','Released':'paid','Refunded':'cancelled','Resolved':'paid' if record.payload.get('worker_amount',0)>0 else 'cancelled'}[status]
        if action=='fund':agreement.funded_hash=record.tx_hash;item.payment_method='escrow_'+agreement.asset.lower()
        if action=='submit':
            Submission.objects.create(assignment=item,author=record.actor,**record.payload)
            item.client_response_due=datetime.fromtimestamp(agreement.review_until,tz=dt_timezone.utc)
        if action=='revise':item.revisions_used=ledger['revisions'];item.client_response_due=None
        if action=='dispute':Dispute.objects.get_or_create(assignment=item,defaults={'opened_by':record.actor,'reason':record.payload['note']})
        if status in ('Released','Refunded','Resolved'):
            agreement.settlement_hash=record.tx_hash
            agreement.worker_paid=agreement.amount if status=='Released' else record.payload.get('worker_amount',0)
            agreement.client_refunded=agreement.amount-agreement.worker_paid
            if agreement.worker_paid:
                Payment.objects.get_or_create(assignment=item,defaults={'amount':agreement.worker_paid,'method':'escrow_'+agreement.asset.lower(),'simulated':False,'network':'stellar_testnet','transaction_hash':record.tx_hash})
            if status=='Resolved':
                resolution='split' if 0<agreement.worker_paid<agreement.amount else 'release' if agreement.worker_paid else 'refund'
                Dispute.objects.filter(assignment=item).update(status='resolved',resolution=resolution,decision_note=record.payload['note'],moderator=record.actor,resolved_at=timezone.now())
            Job.objects.filter(pk=item.job_id).update(status='completed' if agreement.worker_paid else 'closed')
        agreement.save();item.save()
        record.state='confirmed';record.confirmed_at=timezone.now();record.save(update_fields=['state','confirmed_at'])
        Event.objects.create(assignment=item,actor=record.actor,kind='Escrow '+action,note=record.tx_hash)


def reconcile(record):
    rpc=chain.server()
    result=rpc.get_transaction(record.tx_hash)
    if result.status==GetTransactionStatus.SUCCESS:
        apply_confirmed(record,rpc);return True
    if result.status==GetTransactionStatus.FAILED:
        EscrowTransaction.objects.filter(pk=record.pk).exclude(state='confirmed').update(state='failed')
        raise StellarVerificationError('Testnet transaction failed. No escrow state change was recorded; a network fee may have been charged.')
    oldest=getattr(result,'oldest_ledger_close_time',None)
    latest=getattr(result,'latest_ledger_close_time',None)
    if oldest is not None and latest is not None:
        envelope=TransactionEnvelope.from_xdr(record.prepared_xdr,chain.NETWORK)
        bounds=envelope.transaction.preconditions.time_bounds
        # Only expire when RPC history covers the full period in which this
        # transaction could have been signed and included. Missing old history
        # is uncertainty, never proof that funds did not move.
        if bounds and bounds.max_time and oldest<=int(record.created_at.timestamp()) and latest>bounds.max_time:
            EscrowTransaction.objects.filter(pk=record.pk,state__in=['prepared','pending']).update(state='expired')
            raise StellarVerificationError('The request expired without ledger inclusion. Refresh the workroom to prepare a new request.')
    return False
