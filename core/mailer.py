from django.conf import settings
from django.core.mail import send_mail

from .models import EmailDelivery


def send_tracked_email(*,category,subject,message,recipients):
    try:
        sent=send_mail(subject,message,settings.DEFAULT_FROM_EMAIL,recipients,fail_silently=False)
        if sent != 1:
            raise RuntimeError('Email backend did not accept exactly one message.')
    except Exception as exc:
        for recipient in recipients:
            EmailDelivery.objects.create(
                recipient=recipient,category=category,subject=subject,status='failed',
                error_type=type(exc).__name__[:120],
            )
        raise
    for recipient in recipients:
        EmailDelivery.objects.create(recipient=recipient,category=category,subject=subject,status='sent')
    return sent
