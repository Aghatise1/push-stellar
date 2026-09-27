from django.conf import settings
from .models import Assignment, Notification
from .access import staff_role

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
    return {'payment_notice':'Preview · Stellar testnet and simulated payments only.',
            'local_email': not settings.EMAIL_DELIVERY_CONFIGURED,
            'google_auth_enabled': settings.GOOGLE_AUTH_ENABLED,
            'conversation_count':conversation_count,
            'unread_notification_count':unread_notification_count,
            'notification_preview':notification_preview,
            'assigned_active_count':assigned_active_count,
            'work_attention_count':work_attention_count,
            'staff_portal_role':staff_role(request.user)}
