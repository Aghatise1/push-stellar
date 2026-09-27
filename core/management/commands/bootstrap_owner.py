from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from core.models import StaffAccess, User


class Command(BaseCommand):
    help = 'Assign the Owner role to one existing, active, verified Push account.'

    def add_arguments(self, parser):
        parser.add_argument('email')

    def handle(self, *args, **options):
        email = options['email'].strip().lower()
        user = User.objects.filter(email__iexact=email, email_verified=True, is_active=True).first()
        if not user:
            raise CommandError('No active verified Push account uses that email.')
        if not user.is_staff:
            user.is_staff = True
            user.save(update_fields=['is_staff'])
        StaffAccess.objects.update_or_create(
            user=user,
            defaults={
                'role':'owner',
                'status':'approved',
                'approved_at':timezone.now(),
                'approved_by':None,
            },
        )
        self.stdout.write(self.style.SUCCESS(f'Owner access granted to {email}.'))
