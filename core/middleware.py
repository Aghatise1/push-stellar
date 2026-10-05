import logging
import secrets

from django.conf import settings

from .logging import request_id


class AccountActivityMiddleware:
    """Count successful signed-in page use, at most once a minute per session."""
    def __init__(self,get_response):
        self.get_response=get_response

    def __call__(self,request):
        response=self.get_response(request)
        if (request.user.is_authenticated and response.status_code < 400 and
                response.get('Content-Type','').startswith('text/html') and
                request.path != '/activity/status/'):
            from django.utils import timezone
            from django.db import DatabaseError
            from .models import AccountActivity
            now=timezone.now()
            stamp=request.session.get('activity_recorded_at',0)
            if now.timestamp()-stamp >= 60:
                try:
                    AccountActivity.objects.update_or_create(user=request.user,day=timezone.localdate(now),defaults={'last_seen':now})
                except DatabaseError:
                    import logging
                    logging.getLogger(__name__).warning('Account activity could not be recorded.')
                else:
                    request.session['activity_recorded_at']=now.timestamp()
        return response


class AppSecurityMiddleware:
    def __init__(self,get_response):
        self.get_response = get_response
    def __call__(self,request):
        value=request.headers.get('X-Request-ID','').strip()
        if not value or len(value)>64 or not value.replace('-','').isalnum():
            value=secrets.token_hex(12)
        token=request_id.set(value)
        try:
            response = self.get_response(request)
        except Exception:
            logging.getLogger('core.request').exception(
                'Unhandled request error',extra={'path':request.path,'method':request.method}
            )
            raise
        finally:
            request_id.reset(token)
        if (response.status_code >= 400 and
                response.get('Content-Type','').startswith('text/html') and
                not response.streaming and b'<html' not in response.content.lower()):
            from .errors import error_response
            titles = {400:'We could not read that request.',403:'This action is not available.',
                      404:'That page could not be found.',405:'Please use the page controls.',
                      429:'Please wait before trying again.'}
            original = response
            response = error_response(original.status_code,
                titles.get(original.status_code,'We could not complete that request.'),
                original.content.decode(original.charset).strip() or 'Return to Push and try again shortly.')
            for name,header_value in original.items():
                if name.lower() not in {'content-type','content-length','cache-control'}:
                    response[name] = header_value
            response.cookies.update(original.cookies)
        response['X-Request-ID'] = value
        response['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'; object-src 'none'"
        response['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
        response['Cross-Origin-Opener-Policy'] = 'same-origin'
        response['Cross-Origin-Resource-Policy'] = 'same-origin'
        # Render terminates TLS before Django.  Its forwarded request can look
        # non-secure to SecurityMiddleware even though the public response is
        # HTTPS, so emit the configured HSTS policy at the application edge.
        if settings.PRODUCTION and settings.PUSH_ORIGIN.startswith('https://') and settings.SECURE_HSTS_SECONDS:
            hsts=[f'max-age={settings.SECURE_HSTS_SECONDS}']
            if settings.SECURE_HSTS_INCLUDE_SUBDOMAINS:
                hsts.append('includeSubDomains')
            if settings.SECURE_HSTS_PRELOAD:
                hsts.append('preload')
            response['Strict-Transport-Security']='; '.join(hsts)
        if response.status_code == 429 and 'Retry-After' not in response:
            response['Retry-After'] = '900'
        if request.user.is_authenticated or request.path.startswith(('/login/','/reset/','/verify/','/password-reset/')):
            response['Cache-Control'] = 'no-store, private'
        return response


class StaffWorkspaceBoundaryMiddleware:
    """Keep approved non-owner staff accounts in Operations, even with direct URLs."""
    MEMBER_ROUTES = {
        'workspace','analytics','support','support_ticket','work','assigned_work',
        'activity_status','support_feedback','notifications','notifications_read_all','notification_read',
        'inbox','conversation','wallet','payments','wallet_connect','wallet_sync','profile',
        'jobs','job_detail','public_profile','profile_image','resume_download',
        'job_create','job_edit','job_close','apply','select','withdraw',
        'assignment','assignment_message','assignment_action',
    }

    def __init__(self,get_response):
        self.get_response=get_response

    def __call__(self,request):
        return self.get_response(request)

    def process_view(self,request,view_func,view_args,view_kwargs):
        if not request.user.is_authenticated:
            return None
        from django.shortcuts import redirect
        from .access import staff_role
        name=getattr(request.resolver_match,'url_name',None)
        if name in self.MEMBER_ROUTES and staff_role(request.user) in {'admin','trust_support'}:
            return redirect('staff_dashboard')
        return None
