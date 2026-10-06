"""Testnet workroom views; escrow remains disabled until release configuration."""
import hashlib
import json
from datetime import datetime,time,timezone as dt_timezone,timedelta
from django.conf import settings
from django.db import transaction
from django.http import JsonResponse,HttpResponseBadRequest,HttpResponseForbidden
from django.shortcuts import get_object_or_404,render,redirect
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from . import escrow as chain
from .escrow_policy import can_review,action_payload
from .models import Assignment,EscrowAgreement,EscrowTransaction,User,Event,EscrowStaffWallet
from .forms import SubmissionForm,MessageForm
from .stellar import StellarVerificationError,valid_account_id
from .views import verified
from .access import staff_role


def reviewers(item):
    return User.objects.filter(is_active=True,email_verified=True,staff_access__status='approved',staff_access__role__in=['owner','admin','trust_support']).exclude(pk__in=[item.job.owner_id,item.worker_id]).exclude(stellar_address='')


def accessible(request,pk):
    item=get_object_or_404(Assignment.objects.select_related('job__owner','worker'),pk=pk,escrow_required=True)
    if request.user.pk in (item.worker_id,item.job.owner_id):return item
    agreement=EscrowAgreement.objects.filter(assignment=item).first()
    if agreement and can_review(request.user,agreement):return item
    raise PermissionError('Only participants and authorised dispute staff can access this escrow.')


def workroom(request,item):
    agreement=EscrowAgreement.objects.filter(assignment=item).first()
    return render(request,'escrow_assignment.html',{
        'item':item,'escrow':agreement,'is_owner':request.user.pk==item.job.owner_id,
        'is_worker':request.user.pk==item.worker_id,'is_reviewer':bool(agreement and can_review(request.user,agreement)),
        'reviewers':reviewers(item),'submission_form':SubmissionForm(),'message_form':MessageForm(),
        'escrow_enabled':settings.PUSH_TESTNET_ESCROW_ENABLED and bool(settings.PUSH_TESTNET_ESCROW_STAFF_CONTRACT if settings.PUSH_TESTNET_ONLY and not agreement else (agreement.contract if agreement else settings.PUSH_TESTNET_ESCROW_CONTRACT)),
        'staff_governed':agreement.staff_governed if agreement else settings.PUSH_TESTNET_ONLY,
        'pending':agreement.transactions.filter(state__in=['prepared','pending']).first() if agreement else None,
        'now_timestamp':int(timezone.now().timestamp()),
        'delivery_due':datetime.fromtimestamp(agreement.deadline,tz=dt_timezone.utc) if agreement else None,
        'review_due':datetime.fromtimestamp(agreement.review_until,tz=dt_timezone.utc) if agreement and agreement.review_until else None,
    })


@verified
def detail(request,pk):
    try:return workroom(request,accessible(request,pk))
    except PermissionError as exc:return HttpResponseForbidden(str(exc))


def agreement_action(request,item):
    try:chain.require_enabled()
    except StellarVerificationError as exc:return HttpResponseBadRequest(str(exc))
    action=request.POST.get('action')
    with transaction.atomic():
        item=Assignment.objects.select_for_update().select_related('job__owner','worker').get(pk=item.pk)
        agreement=EscrowAgreement.objects.filter(assignment=item).first()
        if item.status!='awaiting_acceptance' and action!='cancel':return HttpResponseBadRequest('Use the wallet-authorised escrow controls.')
        if action=='configure' and request.user.pk==item.job.owner_id and not agreement:
            try:chain.require_enabled()
            except StellarVerificationError as exc:return HttpResponseBadRequest(str(exc))
            contract=settings.PUSH_TESTNET_ESCROW_CONTRACT
            governed=settings.PUSH_TESTNET_ONLY
            if governed:
                contract=settings.PUSH_TESTNET_ESCROW_STAFF_CONTRACT
                if not contract: return HttpResponseBadRequest('The staff escrow contract must be configured before funding can be enabled.')
                try: root_address=chain.registry_owner(contract)
                except Exception:
                    return HttpResponseBadRequest('The testnet staff authority could not be verified. Try again shortly; no tokens were moved.')
                root=EscrowStaffWallet.objects.select_related('user').filter(address=root_address).first()
                if not root or not root.user.is_active or staff_role(root.user)!='owner' or not root.user.email_verified:
                    return HttpResponseBadRequest('The contract owner must register and verify their staff wallet first.')
                reviewer=root.user
                reviewer_address=root.address
            else:
                reviewer=get_object_or_404(reviewers(item),pk=request.POST.get('reviewer'))
                reviewer_address=reviewer.stellar_address
            source=request.session.get('wallet_connected_address','')
            addresses=[source,item.worker.stellar_address,reviewer_address]
            if source!=item.job.owner.stellar_address or not all(valid_account_id(v) for v in addresses) or addresses[0]==addresses[1] or (not governed and len(set(addresses))!=3):
                return HttpResponseBadRequest('Connect your wallet. Client and worker need distinct valid testnet wallets.')
            deadline=int(datetime.combine(item.job.deadline,time.max,tzinfo=dt_timezone.utc).timestamp())
            if deadline<=timezone.now().timestamp():return HttpResponseBadRequest('The delivery deadline has passed.')
            snapshot=item.agreement_snapshot;asset=snapshot.get('payment_asset',item.job.payment_asset)
            EscrowAgreement.objects.create(assignment=item,reviewer=reviewer,contract=contract,staff_governed=governed,
                agreement_id=hashlib.sha256(('push-escrow:'+str(item.pk)).encode()).hexdigest(),client_address=source,
                worker_address=addresses[1],reviewer_address=addresses[2],asset=asset,token_address=chain.token_address(asset),
                amount=item.budget,deadline=deadline,review_seconds=int(snapshot.get('response_days',item.job.response_days))*86400,
                revision_limit=int(snapshot.get('revision_limit',item.job.revision_limit)))
        elif action=='accept' and request.user.pk==item.worker_id and agreement:
            if not agreement.staff_governed and not can_review(agreement.reviewer,agreement):
                return HttpResponseBadRequest('The assigned reviewer is no longer authorised. Cancel this unfunded agreement and prepare new terms.')
            if not request.POST.get('accept_terms') or (agreement.asset=='XLM' and not request.POST.get('accept_xlm')):
                return HttpResponseBadRequest('Accept the agreement and the XLM notice when applicable.')
            if request.session.get('wallet_connected_address')!=agreement.worker_address:
                return HttpResponseBadRequest('Connect the worker wallet named in this agreement.')
            agreement.accepted_at=timezone.now();agreement.xlm_acknowledged=agreement.asset=='XLM';agreement.save()
            item.accepted_terms_at=agreement.accepted_at;item.status='awaiting_funding';item.save(update_fields=['accepted_terms_at','status'])
        elif action=='cancel' and request.user.pk in (item.worker_id,item.job.owner_id) and item.status in ('awaiting_acceptance','awaiting_funding'):
            if agreement and (agreement.chain_status!='Unfunded' or agreement.transactions.filter(state__in=['prepared','pending']).exists()):
                return HttpResponseBadRequest('Check any prepared or pending transaction before cancellation.')
            item.status='cancelled';item.save(update_fields=['status'])
        else:return HttpResponseBadRequest('This action is unavailable. Refresh the workroom.')
        Event.objects.create(assignment=item,actor=request.user,kind=action,note='Testnet escrow agreement terms')
    return redirect('escrow_detail',pk=item.pk)


def request_payload(request):
    try:
        value=json.loads(request.body)
        if not isinstance(value,dict):raise ValueError()
        return value
    except (ValueError,UnicodeError):raise StellarVerificationError('Invalid request.')


@verified
@require_POST
def prepare(request,pk):
    try:
        chain.require_enabled();data=request_payload(request);item=accessible(request,pk)
        with transaction.atomic():
            item=Assignment.objects.select_for_update().get(pk=item.pk)
            agreement=EscrowAgreement.objects.select_for_update().get(assignment=item)
            action=str(data.get('action',''))
            payload=action_payload(item,agreement,request.user,action,data)
            source=(request.user.escrow_staff_wallet.address if agreement.staff_governed else agreement.reviewer_address) if action=='resolve' else agreement.worker_address if request.user.pk==item.worker_id else agreement.client_address
            if request.session.get('staff_wallet_connected_address' if action=='resolve' else 'wallet_connected_address')!=source:
                raise StellarVerificationError('Connect the exact wallet recorded in this agreement.')
            if action=='resolve' and agreement.staff_governed and chain.registry_role(agreement.contract,source)==0:
                raise StellarVerificationError('Your wallet has no active contract permission. An owner or administrator must grant access first.')
            if agreement.transactions.filter(state__in=['prepared','pending']).exists():
                raise StellarVerificationError('A transaction is already prepared or pending. Check its status before preparing another.')
            envelope=chain.build(agreement,action,source,payload)
            record=EscrowTransaction.objects.create(escrow=agreement,actor=request.user,action=action,source=source,
                prepared_xdr=envelope.to_xdr(),tx_hash=envelope.hash_hex(),payload=payload)
        return JsonResponse({'ok':True,'token':str(record.pk),'source':source,'xdr':record.prepared_xdr,
            'networkPassphrase':chain.NETWORK,'fee':str(envelope.transaction.fee/chain.SCALE),
            'message':f'Testnet {action}: {agreement.amount} {agreement.asset}. Network fee is additional.'})
    except (StellarVerificationError,PermissionError,EscrowAgreement.DoesNotExist) as exc:
        return JsonResponse({'ok':False,'message':str(exc)},status=400)
    except Exception:
        return JsonResponse({'ok':False,'message':'Testnet could not prepare this operation. Check balance, USDC trustlines, deadline and contract availability; no funds were recorded.'},status=503)


@verified
@require_POST
def submit(request,pk):
    from .escrow_records import reconcile
    from stellar_sdk.soroban_rpc import SendTransactionStatus
    try:
        chain.require_enabled();item=accessible(request,pk);data=request_payload(request)
        record=get_object_or_404(EscrowTransaction,pk=data.get('token'),escrow__assignment=item)
        if record.actor_id!=request.user.pk:raise PermissionError('Only the preparing account may submit or retry this transaction.')
        if record.action=='resolve' and not can_review(request.user,record.escrow):raise PermissionError('Reviewer access is no longer active.')
        if record.state=='confirmed':return completion(item,record)
        if record.state not in ('prepared','pending'):raise StellarVerificationError('This transaction is closed. Refresh the workroom.')
        if record.state=='prepared':
            if request.session.get('staff_wallet_connected_address' if record.action=='resolve' else 'wallet_connected_address')!=record.source:raise StellarVerificationError('Reconnect the agreement wallet.')
            if timezone.now()-record.created_at>timedelta(minutes=5):
                if reconcile(record):return completion(item,record)
                raise StellarVerificationError('The request is past its approval window. Check status again once the testnet ledger has caught up.')
            if not data.get('signedXdr'):
                return JsonResponse({'ok':False,'message':'Approval was not submitted. Wait five minutes for this unsigned request to expire, then prepare again.'},status=400)
            envelope=chain.validate_signature(record,data['signedXdr'])
            with transaction.atomic():
                locked=EscrowTransaction.objects.select_for_update().get(pk=record.pk)
                if locked.state=='prepared':
                    locked.signed_xdr=envelope.to_xdr();locked.state='pending';locked.save(update_fields=['signed_xdr','state'])
            record.refresh_from_db()
        if reconcile(record):return completion(item,record)
        # Retry the same signed envelope only. Its hash and sequence cannot create a second payment.
        envelope=chain.validate_signature(record,record.signed_xdr)
        result=chain.server().send_transaction(envelope)
        if result.status==SendTransactionStatus.ERROR:
            if reconcile(record):return completion(item,record)
            raise StellarVerificationError('Testnet rejected submission. Check transaction status before preparing another transaction.')
        return JsonResponse({'ok':True,'pending':True,'token':str(record.pk),'message':'Awaiting Stellar ledger confirmation. Do not sign a second payment.'})
    except (StellarVerificationError,PermissionError) as exc:
        return JsonResponse({'ok':False,'message':str(exc)},status=400)
    except Exception:
        return JsonResponse({'ok':False,'message':'Confirmation is unavailable. Use Check transaction status; do not send another payment.'},status=503)


def completion(item,record):
    return JsonResponse({'ok':True,'message':'Stellar testnet escrow transaction confirmed.','redirectUrl':reverse('escrow_detail',args=[item.pk]),'explorerUrl':'https://stellar.expert/explorer/testnet/tx/'+record.tx_hash})


def convert_legacy(request,item):
    from .models import Payment,WalletTransfer
    if request.POST.get('action')!='convert_escrow' or request.user.pk!=item.job.owner_id:
        return HttpResponseBadRequest('This historical workroom cannot create simulated payments. The client may convert an unfunded agreement to testnet escrow.')
    if request.POST.get('confirm_unpaid')!='on':
        return HttpResponseBadRequest('Confirm that no payment was already sent for this agreement.')
    with transaction.atomic():
        item=Assignment.objects.select_for_update().select_related('job').get(pk=item.pk)
        if item.escrow_required or item.status not in ('awaiting_acceptance','awaiting_funding') or Payment.objects.filter(assignment=item).exists() or WalletTransfer.objects.filter(assignment=item).exists():
            return HttpResponseBadRequest('Only an unfunded, unpaid agreement can be converted. Existing settlement records are preserved.')
        snapshot=dict(item.agreement_snapshot)
        snapshot.setdefault('payment_asset','USDC')
        snapshot.setdefault('deadline',item.job.deadline.isoformat())
        snapshot.setdefault('response_days',item.job.response_days)
        snapshot.setdefault('revision_limit',item.job.revision_limit)
        item.agreement_snapshot=snapshot;item.escrow_required=True;item.status='awaiting_acceptance'
        item.accepted_terms_at=None;item.payment_method='';item.client_response_due=None
        item.save(update_fields=['agreement_snapshot','escrow_required','status','accepted_terms_at','payment_method','client_response_due'])
        Event.objects.create(assignment=item,actor=request.user,kind='Testnet conversion',note='Client confirmed no prior payment. Previous records retained; new wallet terms require fresh worker acceptance.')
    return redirect('escrow_detail',pk=item.pk)
