from django.conf import settings
from .models import Notification

def app_context(request):
    conversation_count = 0
    unread_notification_count = 0
    notification_preview = []
    if request.user.is_authenticated:
        notice_qs = Notification.objects.filter(recipient=request.user,read_at__isnull=True)
        conversation_count = notice_qs.filter(kind='message').count()
        unread_notification_count = notice_qs.count()
        notification_preview = notice_qs[:5]
    return {'payment_notice':'Preview · Stellar testnet and simulated payments only.',
            'local_email': not settings.EMAIL_DELIVERY_CONFIGURED,
            'google_auth_enabled': settings.GOOGLE_AUTH_ENABLED,
            'conversation_count':conversation_count,
            'unread_notification_count':unread_notification_count,
            'notification_preview':notification_preview}
