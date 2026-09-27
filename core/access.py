from functools import wraps

from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse
from urllib.parse import urlencode


def staff_role(user):
    if not getattr(user,'is_authenticated',False):
        return None
    if user.is_superuser:
        return 'owner'
    access=getattr(user,'staff_access',None)
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
