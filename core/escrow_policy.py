"""Pure permission and payload validation for the configurable testnet escrow flow."""
from .access import has_staff_access
from .forms import SubmissionForm
from .stellar import StellarVerificationError


def can_review(user,agreement):
    if getattr(agreement,'staff_governed',False):
        from .models import EscrowStaffWallet
        item=agreement.assignment
        if user.pk in (item.job.owner_id,item.worker_id): return False
        wallet=EscrowStaffWallet.objects.filter(user=user).first()
        return bool(wallet and wallet.address not in (agreement.client_address,agreement.worker_address)
                    and user.is_active and user.email_verified and has_staff_access(user,{'owner','admin','trust_support'}))
    return user.pk==agreement.reviewer_id and has_staff_access(user,{'owner','admin','trust_support'})


def action_payload(item,agreement,user,action,data):
    owner=user.pk==item.job.owner_id
    worker=user.pk==item.worker_id
    state=agreement.chain_status
    allowed={
        'fund':owner and state=='Unfunded' and item.status=='awaiting_funding' and agreement.accepted_at is not None,
        'submit':worker and state=='Funded',
        'approve':owner and state=='Submitted',
        'revise':owner and state=='Submitted',
        'dispute':(owner or worker) and state in ('Funded','Submitted'),
        'refund_expired':owner and state=='Funded',
        'claim_expired':worker and state=='Submitted',
        'resolve':can_review(user,agreement) and state=='Disputed',
    }
    if not allowed.get(action):
        raise StellarVerificationError('This escrow action is not permitted in the current state.')
    if action=='submit':
        form=SubmissionForm(data)
        if not form.is_valid():
            raise StellarVerificationError('Provide valid delivery notes and an optional deliverable link.')
        return dict(form.cleaned_data)
    if action in ('dispute','revise','resolve'):
        note=str(data.get('note','')).strip()
        if not note or len(note)>500:
            raise StellarVerificationError('Provide a reason of up to 500 characters.')
        result={'note':note}
        if action=='resolve':
            try: worker_amount=int(str(data.get('worker_amount','')))
            except ValueError: raise StellarVerificationError('Enter a whole-token worker share.')
            if not 0<=worker_amount<=agreement.amount:
                raise StellarVerificationError('Worker share must be within the locked amount.')
            result.update(worker_amount=worker_amount,client_amount=agreement.amount-worker_amount)
        return result
    return {}
