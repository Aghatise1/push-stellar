from functools import wraps

from django.conf import settings
from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from urllib.parse import urlencode

from .models import StaffAccess, User


def staff_role(user):
    if not getattr(user,'is_authenticated',False):
        return None
    if user.is_superuser:
        return 'owner'
    access=getattr(user,'staff_access',None)
    # A protected environment allow-list can establish the first recovery
    # owner after Google has verified and created the account. It never stores
    # a password and never silently restores revoked access.
    if (not access and user.is_active and user.email_verified and
            user.email.strip().lower() in settings.PUSH_BOOTSTRAP_OWNER_EMAILS):
        access=StaffAccess.objects.create(
            user=user,role='owner',status='approved',approved_at=timezone.now()
        )
        if not user.is_staff:
            User.objects.filter(pk=user.pk).update(is_staff=True)
            user.is_staff=True
    if access and access.status == 'approved' and user.is_active:
        return access.role
    return None


def has_staff_access(user,roles=None):
    role=staff_role(user)
    return bool(role and (roles is None or role in roles))


def staff_only(*roles):
    def decorator(view):
        @wraps(view)
        def wrapped(request,*args,**kwargs):
            if not getattr(request.user,'is_authenticated',False):
                query=urlencode({'next':request.get_full_path()})
                return redirect(f'{reverse("staff_login")}?{query}')
            if not has_staff_access(request.user,set(roles) if roles else None):
                # Do not advertise the operations surface to ordinary accounts.
                raise Http404
            return view(request,*args,**kwargs)
        return wrapped
    return decorator
