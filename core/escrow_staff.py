"""Staff wallet proof and wallet-signed, on-chain dispute permissions. No secrets."""
import secrets
from datetime import timedelta
from django.conf import settings
from django.db import transaction, IntegrityError
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from stellar_sdk import Account, TransactionBuilder, TransactionEnvelope
from stellar_sdk.soroban_rpc import GetTransactionStatus, SendTransactionStatus
from . import escrow as chain
from .access import staff_only, staff_role
from .models import User, EscrowStaffWallet, EscrowStaffOperation, AuditEvent
from .stellar import StellarVerificationError, valid_account_id
from .escrow_views import request_payload


def eligible(user):
    if not user.is_active or not user.email_verified or staff_role(user) not in ('owner','admin','trust_support'):
        raise StellarVerificationError('An active, email-verified Owner, Admin or Trust & Support account is required.')


def permission(actor,target,role):
    eligible(actor)
    actor_role=staff_role(actor)
    target_role=staff_role(target)
    if actor==target or actor_role not in ('owner','admin'):
        raise StellarVerificationError('Another authorised owner or admin must manage this permission.')
    if actor_role=='admin' and (target_role in ('owner','admin') or role==2):
        raise StellarVerificationError('Only the owner can manage administrator wallets.')
    if role:
        eligible(target)
        expected=2 if target_role in ('owner','admin') else 1
        if role!=expected: raise StellarVerificationError('The wallet permission must match the approved Push staff role.')


@staff_only('owner','admin','trust_support')
def panel(request):
    wallets=EscrowStaffWallet.objects.select_related('user').order_by('user__email')
    return render(request,'escrow_staff.html',{
        'wallets':wallets,'registered':wallets.filter(user=request.user).first(),
        'manager':staff_role(request.user) in ('owner','admin'),
        'contract':settings.PUSH_TESTNET_ESCROW_STAFF_CONTRACT,
        'operations':EscrowStaffOperation.objects.filter(actor=request.user,state__in=['prepared','pending']).order_by('-created_at'),
    })


@staff_only('owner','admin','trust_support')
@require_POST
def prepare(request):
    try:
        eligible(request.user); data=request_payload(request)
        action=data.get('action'); contract=''; role=0
        with transaction.atomic():
            # Serialize proofs and management operations by the signing account.
            actor=User.objects.select_for_update().get(pk=request.user.pk)
            if action=='prove':
                target=actor; wallet=str(data.get('wallet','')).strip(); source=wallet
                if not valid_account_id(wallet): raise StellarVerificationError('Provide a Stellar public G-address.')
                existing=EscrowStaffWallet.objects.filter(user=actor).first()
                if existing: raise StellarVerificationError('This account already has a verified staff wallet. Revoke its contract permissions before arranging wallet replacement.')
                if EscrowStaffWallet.objects.filter(address=wallet).exists(): raise StellarVerificationError('This wallet already belongs to another staff account.')
                # Sequence 0 cannot be submitted for a funded Stellar account. This
                # signed proof is checked locally and NEVER sent to the network.
                proof=chain.digest({'user':actor.pk,'email':actor.email,'nonce':secrets.token_hex(32),'purpose':'Push staff wallet proof'})
                envelope=(TransactionBuilder(Account(wallet,-1),chain.NETWORK,base_fee=100)
                    .append_manage_data_op('Push staff wallet proof',proof).set_timeout(300).build())
            elif action=='set_staff':
                chain.require_enabled(); contract=settings.PUSH_TESTNET_ESCROW_STAFF_CONTRACT
                if not contract: raise StellarVerificationError('The staff escrow contract has not been configured.')
                target=get_object_or_404(User,pk=data.get('target'))
                role=int(data.get('role',-1))
                if role not in (0,1,2): raise StellarVerificationError('Choose reviewer, administrator or revoke.')
                permission(actor,target,role)
                source=get_object_or_404(EscrowStaffWallet,user=actor).address
                wallet=get_object_or_404(EscrowStaffWallet,user=target).address
                if request.session.get('staff_wallet_connected_address')!=source:
                    raise StellarVerificationError('Connect your verified staff wallet from Escrow staff access.')
                if EscrowStaffOperation.objects.filter(actor=actor,action='set_staff',state__in=['prepared','pending']).exists():
                    raise StellarVerificationError('Check your pending permission change before preparing another.')
                envelope=chain.build_staff(contract,source,wallet,role)
            else: raise StellarVerificationError('Unsupported staff operation.')
            record=EscrowStaffOperation.objects.create(actor=actor,target=target,action=action,contract=contract,
                source=source,wallet=wallet,role=role,prepared_xdr=envelope.to_xdr(),tx_hash=envelope.hash_hex())
        return JsonResponse({'ok':True,'token':str(record.pk),'source':source,'xdr':record.prepared_xdr,'networkPassphrase':chain.NETWORK,
            'message':'Sign wallet ownership proof. No transaction will be broadcast.' if action=='prove' else f'Review permission change for {target.email}: role {role} (0 revoked, 1 reviewer, 2 administrator).'})
    except (StellarVerificationError,ValueError) as exc:
        return JsonResponse({'ok':False,'message':str(exc)},status=400)
    except Exception:
        return JsonResponse({'ok':False,'message':'Could not prepare this operation. Check the registered wallets, contract and connection.'},status=503)


def confirmed(record):
    with transaction.atomic():
        locked=EscrowStaffOperation.objects.select_for_update().get(pk=record.pk)
        if locked.state=='confirmed': return
        if locked.action=='prove':
            EscrowStaffWallet.objects.create(user=locked.actor,address=locked.wallet)
        locked.state='confirmed';locked.confirmed_at=timezone.now();locked.save(update_fields=['state','confirmed_at'])
        AuditEvent.objects.create(actor=locked.actor,action='escrow.staff.'+locked.action,target_type='User',target_id=str(locked.target_id),
            detail={'wallet':locked.wallet,'role':locked.role,'contract':locked.contract,'transaction':locked.tx_hash})


@staff_only('owner','admin','trust_support')
@require_POST
def submit(request):
    try:
        eligible(request.user); data=request_payload(request)
        record=get_object_or_404(EscrowStaffOperation,pk=data.get('token'),actor=request.user)
        if record.state=='confirmed': return done()
        if record.state not in ('prepared','pending'): raise StellarVerificationError('This request is closed. Prepare a new request.')
        if record.action=='prove':
            if timezone.now()-record.created_at>timedelta(minutes=5):
                EscrowStaffOperation.objects.filter(pk=record.pk).update(state='expired')
                raise StellarVerificationError('Wallet proof expired. Register again.')
            chain.validate_signature(record,data.get('signedXdr'))
            confirmed(record); return done()
        chain.require_enabled(); rpc=chain.server()
        # Reconcile even if the target was revoked in Push after signing.
        result=rpc.get_transaction(record.tx_hash)
        if result.status==GetTransactionStatus.SUCCESS:
            confirmed(record); return done()
        if result.status==GetTransactionStatus.FAILED:
            EscrowStaffOperation.objects.filter(pk=record.pk).update(state='failed')
            raise StellarVerificationError('Permission change failed on testnet. Check current access before retrying.')
        bounds=TransactionEnvelope.from_xdr(record.prepared_xdr,chain.NETWORK).transaction.preconditions.time_bounds
        oldest=getattr(result,'oldest_ledger_close_time',None);latest=getattr(result,'latest_ledger_close_time',None)
        if oldest is not None and latest is not None and oldest<=int(record.created_at.timestamp()) and latest>bounds.max_time:
            EscrowStaffOperation.objects.filter(pk=record.pk).update(state='expired')
            raise StellarVerificationError('Request expired without ledger inclusion. Refresh to prepare again.')
        permission(request.user,record.target,record.role)
        if record.state=='prepared':
            if timezone.now()-record.created_at>timedelta(minutes=5): raise StellarVerificationError('Approval expired. Check status after the ledger catches up.')
            if request.session.get('staff_wallet_connected_address')!=record.source: raise StellarVerificationError('Reconnect your registered staff wallet.')
            envelope=chain.validate_signature(record,data.get('signedXdr'))
            with transaction.atomic():
                locked=EscrowStaffOperation.objects.select_for_update().get(pk=record.pk)
                if locked.state=='prepared':
                    locked.signed_xdr=envelope.to_xdr();locked.state='pending';locked.save(update_fields=['signed_xdr','state'])
            record.refresh_from_db()
        result=rpc.send_transaction(chain.validate_signature(record,record.signed_xdr))
        if result.status==SendTransactionStatus.ERROR: raise StellarVerificationError('Network rejected this change. Check status before preparing again.')
        return JsonResponse({'ok':True,'pending':True,'message':'Waiting for confirmed testnet permission change.'})
    except (StellarVerificationError,ValueError,IntegrityError) as exc:
        return JsonResponse({'ok':False,'message':str(exc) if not isinstance(exc,IntegrityError) else 'Wallet already registered. Refresh the page.'},status=400)
    except Exception:
        return JsonResponse({'ok':False,'message':'Confirmation unavailable. Check status before signing another permission change.'},status=503)


@staff_only('owner','admin','trust_support')
@require_POST
def status(request):
    try:
        data=request_payload(request); wallet=get_object_or_404(EscrowStaffWallet,pk=data.get('wallet'))
        contract=settings.PUSH_TESTNET_ESCROW_STAFF_CONTRACT
        if not contract: raise StellarVerificationError('Staff escrow contract is not yet configured.')
        role=chain.registry_role(contract,wallet.address)
        return JsonResponse({'ok':True,'message':f'{wallet.user.email}: confirmed contract permission — '+{0:'revoked / not granted',1:'reviewer',2:'administrator',3:'deployment owner'}[role]})
    except StellarVerificationError as exc: return JsonResponse({'ok':False,'message':str(exc)},status=400)
    except Exception: return JsonResponse({'ok':False,'message':'Could not verify on-chain permission. Treat it as unknown until checked.'},status=503)


def done():
    return JsonResponse({'ok':True,'message':'Confirmed. Use Check on-chain access to verify the current permission.','redirectUrl':reverse('escrow_staff')})


@staff_only('owner','admin','trust_support')
@require_POST
def wallet_connection(request, operation):
    try:
        eligible(request.user)
        data=request_payload(request)
        key='staff_wallet_connected_address'
        saved=request.session.get('staff_wallet_selected_address','')
        if operation=='disconnect':
            request.session.pop(key,None)
            request.session.pop('staff_wallet_challenge',None)
            request.session['staff_wallet_disconnected']=True
        else:
            address=str(data.get('address','')).strip()
            valid=valid_account_id(address) and str(data.get('network','')).upper()=='TESTNET'
            if operation=='connect':
                if not valid: raise StellarVerificationError('Connect a valid Stellar testnet wallet in Freighter.')
                proof=request.session.get('staff_wallet_challenge')
                if not data.get('signedXdr'):
                    request.session.pop(key,None)
                    request.session['staff_wallet_disconnected']=True
                    envelope=(TransactionBuilder(Account(address,-1),chain.NETWORK,base_fee=100)
                        .append_manage_data_op('Push staff connection',secrets.token_bytes(32)).set_timeout(300).build())
                    request.session['staff_wallet_challenge']={'hash':envelope.hash_hex(),'address':address,'user':request.user.pk,'expires':timezone.now().timestamp()+300}
                    return JsonResponse({'ok':True,'requiresApproval':True,'xdr':envelope.to_xdr(),'source':address,'networkPassphrase':chain.NETWORK})
                if not proof or proof['user']!=request.user.pk or proof['address']!=address or proof['expires']<timezone.now().timestamp():
                    raise StellarVerificationError('Connection approval expired. Connect again.')
                from types import SimpleNamespace
                chain.validate_signature(SimpleNamespace(tx_hash=proof['hash'],source=address),data['signedXdr'])
                request.session.pop('staff_wallet_challenge',None)
                request.session['staff_wallet_selected_address']=saved=address
                request.session.pop('staff_wallet_disconnected',None)
                request.session[key]=address
            elif valid and data.get('connected') and address==saved and request.session.get(key)==address and not request.session.get('staff_wallet_disconnected'):
                request.session[key]=address
            else:
                request.session.pop(key,None)
        active=request.session.get(key,'')
        return JsonResponse({'ok':True,'connected':bool(active),'state':'connected' if active else 'disconnected','activeAddress':active,'savedAddress':saved,'address':active,'message':'Staff wallet connected on testnet. Settlement still requires your signature.' if active else 'Staff wallet disconnected. Reconnect Freighter to sign.'})
    except (StellarVerificationError,ValueError) as exc:
        return JsonResponse({'ok':False,'message':str(exc)},status=400)
