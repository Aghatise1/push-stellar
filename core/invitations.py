from django.utils import timezone
from django.utils.crypto import salted_hmac

from .models import Invitation


SESSION_KEY = 'push_invitation_id'


def hash_invitation_code(code):
    return salted_hmac('push.invitation.code',code.strip().upper()).hexdigest()


def current_invitation(request, email=None, for_update=False):
    invitation_id=request.session.get(SESSION_KEY)
    if not invitation_id:
        return None
    queryset=Invitation.objects.select_for_update() if for_update else Invitation.objects
    invitation=queryset.filter(
        pk=invitation_id,used_at__isnull=True,revoked_at__isnull=True,expires_at__gt=timezone.now(),
    ).first()
    if invitation is None:
        request.session.pop(SESSION_KEY,None)
        return None
    if email and invitation.email.casefold() != email.strip().casefold():
        return None
    return invitation


def remember_invitation(request, invitation):
    request.session[SESSION_KEY]=str(invitation.pk)


def consume_invitation(request, user, invitation=None):
    invitation=invitation or current_invitation(request,user.email,for_update=True)
    if invitation is None:
        return False
    invitation.used_at=timezone.now()
    invitation.used_by=user
    invitation.save(update_fields=['used_at','used_by'])
    request.session.pop(SESSION_KEY,None)
    return True
