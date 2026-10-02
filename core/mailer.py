import hashlib
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from .models import EmailDelivery, RateBucket


class EmailDailyLimitError(RuntimeError):
    pass


def _reserve_daily_email_capacity(recipient_count):
    """Reserve recipient capacity before contacting the paid email provider."""
    today=timezone.localdate().isoformat()
    key=hashlib.sha256(f'email-daily:{today}'.encode()).hexdigest()
    now=timezone.now()
    tomorrow=(now+timedelta(days=1)).replace(hour=0,minute=0,second=0,microsecond=0)
    with transaction.atomic():
        bucket,_=RateBucket.objects.get_or_create(key=key,defaults={'expires':tomorrow})
        if bucket.expires <= now:
            RateBucket.objects.filter(pk=bucket.pk).update(count=0,expires=tomorrow)
        reserved=RateBucket.objects.filter(
            pk=bucket.pk,count__lte=settings.PUSH_EMAIL_DAILY_LIMIT-recipient_count
        ).update(count=F('count')+recipient_count)
    if not reserved:
        raise EmailDailyLimitError('Daily transactional email safety limit reached.')


def send_tracked_email(*,category,subject,message,recipients,invitation=None):
    recipients=list(dict.fromkeys(recipients))
    if not recipients:
        raise ValueError('At least one email recipient is required.')
    try:
        _reserve_daily_email_capacity(len(recipients))
        sent=send_mail(subject,message,settings.DEFAULT_FROM_EMAIL,recipients,fail_silently=False)
        if sent != 1:
            raise RuntimeError('Email backend did not accept exactly one message.')
    except Exception as exc:
        for recipient in recipients:
            EmailDelivery.objects.create(
                recipient=recipient,category=category,subject=subject,status='failed',
                error_type=type(exc).__name__[:120],invitation=invitation,
            )
        raise
    for recipient in recipients:
        EmailDelivery.objects.create(
            recipient=recipient,category=category,subject=subject,status='sent',invitation=invitation,
        )
    return sent
