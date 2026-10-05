from django.conf import settings
from .models import Assignment, Notification
from .access import staff_role

STAFF_PORTAL_ROUTES = {
    'staff_entry', 'staff_dashboard', 'owner_dashboard', 'admin_dashboard',
    'trust_support_dashboard', 'moderation', 'staff_invitations',
    'moderate_dispute', 'moderate_job', 'review_waitlist', 'staff_team', 'staff_guide',
    'operations_tickets', 'operations_ticket', 'operations_users',
    'operations_user', 'operations_email', 'operations_payments',
    'operations_docs', 'operations_docs_edit', 'documentation',
    'documentation_article', 'help', 'operations_analytics', 'lift_sanction',
    'account_settings', 'password_change', 'password_change_done',
}

PUBLIC_INDEX_ROUTES = {
    'home', 'about', 'product', 'how_it_works', 'investors', 'terms', 'privacy',
    'cookies', 'refunds', 'help', 'documentation', 'documentation_article',
}

def app_context(request):
    conversation_count = 0
    unread_notification_count = 0
    notification_preview = []
    assigned_active_count = 0
    work_attention_count = 0
    if request.user.is_authenticated:
        notice_qs = Notification.objects.filter(recipient=request.user,read_at__isnull=True)
        conversation_count = notice_qs.filter(kind='message').count()
        unread_notification_count = notice_qs.count()
        notification_preview = notice_qs[:5]
        assigned_qs = Assignment.objects.filter(worker=request.user)
        assigned_active_count = assigned_qs.exclude(status__in=['paid','cancelled']).count()
        worker_actions = assigned_qs.filter(status__in=['awaiting_acceptance','funded']).count()
        client_actions = Assignment.objects.filter(
            job__owner=request.user,status__in=['awaiting_funding','submitted']
        ).count()
        work_attention_count = worker_actions + client_actions
        saved_wallet_address = request.user.stellar_address
        connected_wallet_address = request.session.get('wallet_connected_address','')
        wallet_session_connected = bool(
            saved_wallet_address and connected_wallet_address == saved_wallet_address
        )
    else:
        saved_wallet_address = ''
        connected_wallet_address = ''
        wallet_session_connected = False
    resolved_name = getattr(getattr(request, 'resolver_match', None), 'url_name', None)
    portal_role = staff_role(request.user)
    public_origin = settings.PUSH_ORIGIN.rstrip('/')
    canonical_path = request.path if request.path.endswith('/') else f'{request.path}/'
    seo_indexable = not request.user.is_authenticated and resolved_name in PUBLIC_INDEX_ROUTES
    return {'payment_notice':'Preview · Stellar testnet and simulated payments only.',
            'local_email': not settings.EMAIL_DELIVERY_CONFIGURED,
            'google_auth_enabled': settings.GOOGLE_AUTH_ENABLED,
            'conversation_count':conversation_count,
            'unread_notification_count':unread_notification_count,
            'notification_preview':notification_preview,
            'assigned_active_count':assigned_active_count,
            'work_attention_count':work_attention_count,
            'saved_wallet_address':saved_wallet_address,
            'connected_wallet_address':connected_wallet_address,
            'wallet_session_connected':wallet_session_connected,
            'staff_portal_role':portal_role,
            'staff_portal_role_label':{'owner':'Owner','admin':'Administrator','trust_support':'Trust & Support'}.get(portal_role,''),
            'staff_is_owner':portal_role == 'owner',
            'staff_portal_active':bool(portal_role and resolved_name in STAFF_PORTAL_ROUTES),
            'seo_indexable':seo_indexable,
            'canonical_url':f'{public_origin}{canonical_path}',
            'seo_image_url':f'{public_origin}{settings.STATIC_URL}images/push-social-card-v3.png'}
