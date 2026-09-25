from django.core.management.base import BaseCommand, CommandError
from core.models import User

class Command(BaseCommand):
    help='Grant Trust Desk access to one existing, verified account.'
    def add_arguments(self,parser):
        parser.add_argument('email')
    def handle(self,*args,**options):
        email=options['email'].strip().lower()
        user=User.objects.filter(email__iexact=email,email_verified=True,is_active=True).first()
        if not user:
            raise CommandError('No active verified account uses that email.')
        if user.is_staff:
            self.stdout.write(self.style.WARNING('That account is already a moderator.'))
            return
        user.is_staff=True;user.save(update_fields=['is_staff'])
        self.stdout.write(self.style.SUCCESS('Moderator access granted.'))
