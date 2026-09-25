from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import RateBucket

class Command(BaseCommand):
    help='Delete expired rate-limit buckets. Run alongside Django clearsessions.'
    def handle(self,*args,**options):
        count,_=RateBucket.objects.filter(expires__lt=timezone.now()).delete()
        self.stdout.write(f'Removed {count} expired rate-limit buckets.')
