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
        response = self.get_response(request)
        response['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'; object-src 'none'"
        response['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
        if request.user.is_authenticated or request.path.startswith(('/login/','/reset/','/verify/','/password-reset/')):
            response['Cache-Control'] = 'no-store, private'
        return response


class StaffWorkspaceBoundaryMiddleware:
    """Keep approved non-owner staff accounts in Operations, even with direct URLs."""
    MEMBER_ROUTES = {
        'workspace','analytics','support','support_ticket','work','assigned_work',
        'activity_status','support_feedback','notifications','notifications_read_all','notification_read',
        'inbox','conversation','wallet','payments','wallet_connect','profile',
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
        if name in self.MEMBER_ROUTES and staff_role(request.user) in {'admin','moderator','support'}:
            return redirect('staff_dashboard')
        return None
