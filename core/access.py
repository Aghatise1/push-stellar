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

from config.security import validated_client_ip
from .models import RateBucket, StaffAccess, User


def client_ip(request):
    """Return the validated client IP under the configured trusted proxy policy."""
    return validated_client_ip(request, getattr(settings, 'PUSH_TRUSTED_PROXIES', ()))


def request_identity(request, scope, *, subject=None, include_ip=False):
    """Build a hashed rate-limit bucket key without storing raw identifiers."""
    source = client_ip(request)
    user = getattr(request, 'user', None)
    if subject is not None:
        norm_subject = str(subject).strip().casefold()
        raw = f'{scope}:subject:{norm_subject}:{source}' if include_ip else f'{scope}:subject:{norm_subject}'
    elif getattr(user, 'is_authenticated', False):
        base = scope if scope.endswith(f':{user.pk}') else f'{scope}:user:{user.pk}'
        raw = f'{base}:{source}' if include_ip else base
    else:
        raw = f'{scope}:ip:{source}'
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


def consume_rate_bucket(key, limit, window=timedelta(minutes=15)):
    now = timezone.now()
    with transaction.atomic():
        bucket, _ = RateBucket.objects.get_or_create(
            key=key, defaults={'expires': now + window}
        )
        if bucket.expires <= now:
            RateBucket.objects.filter(pk=bucket.pk, expires__lte=now).update(
                count=0, expires=now + window
            )
        return RateBucket.objects.filter(pk=bucket.pk, count__lt=limit).update(count=F('count') + 1) == 0


def rate_limited(request, scope, limit=12, *, subject=None, recipient=None, recipient_limit=None, include_ip=False, ip_limit=None):
    primary_key = request_identity(request, scope, subject=subject, include_ip=include_ip)
    is_limited = consume_rate_bucket(primary_key, limit)
    if recipient:
        norm_recipient = str(recipient).strip().casefold()
        if norm_recipient:
            rec_key = hashlib.sha256(f'{scope}:recipient:{norm_recipient}'.encode('utf-8')).hexdigest()
            if consume_rate_bucket(rec_key, recipient_limit or limit):
                is_limited = True
    if ip_limit is not None:
        ip_key = hashlib.sha256(f'{scope}:ip:{client_ip(request)}'.encode('utf-8')).hexdigest()
        if consume_rate_bucket(ip_key, ip_limit):
            is_limited = True
    return is_limited


def _staff_write_limited(request,limit=120):
    """Bound privileged writes per account and source address."""
    if request.method != 'POST':
        return False
    return rate_limited(request, 'staff-write', limit=limit, include_ip=True)


def staff_role(user):
    if not getattr(user,'is_authenticated',False):
        return None
    access=getattr(user,'staff_access',None)
    if user.is_superuser and user.is_active and (not access or access.status == 'approved'):
        return 'owner'
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
