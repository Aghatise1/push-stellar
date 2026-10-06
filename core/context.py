from django.conf import settings
from django.db.models import Q
from .models import Assignment, Notification
from .access import staff_role

STAFF_PORTAL_ROUTES = {
    'escrow_staff', 'staff_entry', 'staff_dashboard', 'owner_dashboard', 'admin_dashboard',
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
    has_project_conversations = False
    conversation_count = 0
    unread_notification_count = 0
    notification_preview = []
    assigned_active_count = 0
    work_attention_count = 0
    if request.user.is_authenticated:
        has_project_conversations = Assignment.objects.filter(Q(worker=request.user)|Q(job__owner=request.user)).filter(~Q(status='awaiting_acceptance')|Q(messages__isnull=False)).exists()
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
    if portal_role:
        saved_wallet_address=request.session.get('staff_wallet_selected_address','')
        connected_wallet_address=request.session.get('staff_wallet_connected_address','')
        wallet_session_connected=bool(connected_wallet_address and connected_wallet_address==saved_wallet_address)
    public_origin = settings.PUSH_ORIGIN.rstrip('/')
    canonical_path = request.path if request.path.endswith('/') else f'{request.path}/'
    seo_indexable = settings.PUSH_DEPLOYMENT_TIER != 'staging' and not request.user.is_authenticated and resolved_name in PUBLIC_INDEX_ROUTES
    return {'payment_notice':'Stellar testnet · Test tokens have no monetary value.',
            'testnet_only':settings.PUSH_TESTNET_ONLY,
            'escrow_live':bool(settings.PUSH_TESTNET_ESCROW_ENABLED and settings.PUSH_TESTNET_ESCROW_STAFF_CONTRACT),
            'is_staging':settings.PUSH_DEPLOYMENT_TIER == 'staging',
            'local_email': not settings.EMAIL_DELIVERY_CONFIGURED,
            'google_auth_enabled': settings.GOOGLE_AUTH_ENABLED,
            'has_project_conversations':has_project_conversations,
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
            'staff_portal_active':bool(portal_role),
            'seo_indexable':seo_indexable,
            'canonical_url':f'{public_origin}{canonical_path}',
            'seo_image_url':f'{public_origin}{settings.STATIC_URL}images/push-social-card-v3.png'}
