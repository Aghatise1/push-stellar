import hashlib
from datetime import timedelta
from functools import wraps

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import F
from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from urllib.parse import urlencode

from .models import RateBucket, StaffAccess, User


def _staff_write_limited(request,limit=120):
    """Bound privileged writes per account and source address."""
    if request.method != 'POST':
        return False
    source=request.META.get('REMOTE_ADDR','unknown')
    raw=f'staff-write:{request.user.pk}:{source}'
    key=hashlib.sha256(raw.encode()).hexdigest()
    now=timezone.now()
    with transaction.atomic():
        bucket,_=RateBucket.objects.get_or_create(
            key=key,defaults={'expires':now+timedelta(minutes=15)}
        )
        if bucket.expires <= now:
            RateBucket.objects.filter(pk=bucket.pk).update(
                count=0,expires=now+timedelta(minutes=15)
            )
        return RateBucket.objects.filter(pk=bucket.pk,count__lt=limit).update(count=F('count')+1) == 0


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
                raise PermissionDenied('Approved Push staff access is required.')
            if _staff_write_limited(request):
                return HttpResponse('Too many staff actions. Try again in 15 minutes.',status=429)
            return view(request,*args,**kwargs)
        return wrapped
    return decorator
