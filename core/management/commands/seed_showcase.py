from datetime import timedelta
import secrets

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from core.models import Application, Assignment, Event, Job, Submission, User, Message


class Command(BaseCommand):
    help = 'Create local-only reviewer accounts and a representative Push workflow.'

    def add_arguments(self, parser):
        parser.add_argument('--rotate-passwords', action='store_true')

    def handle(self, *args, **options):
        if settings.PRODUCTION:
            raise CommandError('Showcase accounts are disabled in production.')

        with transaction.atomic():
            atise, atise_created = User.objects.get_or_create(
                username='atise.demo@push.local',
                defaults={'email':'atise.demo@push.local','display_name':'Atise','email_verified':True,
                          'public_profile':True,'bio':'Independent product builder exploring better infrastructure for Web3 work.',
                          'skills':'Product strategy, community, research'},
            )
            studio, studio_created = User.objects.get_or_create(
                username='studio.demo@push.local',
                defaults={'email':'studio.demo@push.local','display_name':'Demo Studio','email_verified':True,
                          'public_profile':True,'bio':'A sample hiring organisation used to demonstrate the Push workflow.',
                          'skills':'Product, design, engineering'},
            )

            credentials_path = settings.BASE_DIR / 'private-demo-credentials.txt'
            rotate = options['rotate_passwords'] or atise_created or studio_created or not credentials_path.exists()
            if rotate:
                atise_password = self._password()
                studio_password = self._password()
                atise.set_password(atise_password)
                studio.set_password(studio_password)
                atise.save()
                studio.save()
                credentials_path.write_text(
                    'LOCAL PUSH SHOWCASE ACCOUNTS\nThese credentials are for the private development build only.\n\n'
                    f'ATISE\nEmail: {atise.email}\nPassword: {atise_password}\n\n'
                    f'DEMO STUDIO\nEmail: {studio.email}\nPassword: {studio_password}\n', encoding='utf-8')

            deadline = timezone.localdate() + timedelta(days=21)
            active_job, _ = Job.objects.update_or_create(
                owner=studio, title='Prepare the Push hackathon product walkthrough',
                defaults={'project':'Push Review Build','description':'Create a concise walkthrough showing how a Web3 team can publish a brief, select a contributor and preserve delivery evidence.',
                          'deliverables':'A structured walkthrough, annotated product screens and a two-minute reviewer path.',
                          'category':'Content','budget':650,'deadline':deadline,'status':'assigned','demo':False})
            Application.objects.update_or_create(
                job=active_job, worker=atise,
                defaults={'proposal':'I will turn the current workflow into a focused reviewer story and document each product decision.','withdrawn':False})
            assignment, _ = Assignment.objects.update_or_create(
                job=active_job,
                defaults={'worker':atise,'scope':active_job.deliverables,'budget':active_job.budget,
                          'status':'submitted','payment_method':'bank_card'})
            Submission.objects.get_or_create(
                assignment=assignment, author=atise,
                notes='First reviewer walkthrough submitted with the marketplace journey and current limitations clearly labelled.',
                defaults={'link':'https://example.com/push-demo-delivery'})
            for actor, kind, note in [
                (studio,'Worker selected','Atise selected for the showcase assignment.'),
                (atise,'accept','Scope accepted for the local showcase.'),
                (studio,'fund','Bank/card simulation selected; no money moved.'),
                (atise,'submit','Reviewer walkthrough submitted for approval.')]:
                Event.objects.get_or_create(assignment=assignment, actor=actor, kind=kind, note=note)
            Message.objects.get_or_create(assignment=assignment,sender=studio,body='Please keep the reviewer journey under two minutes and make the payment limitations explicit.')
            Message.objects.get_or_create(assignment=assignment,sender=atise,body='Understood. The first walkthrough is attached and the testnet labels are visible throughout.')
            Job.objects.update_or_create(
                owner=atise, title='Design a compact trust-status component',
                defaults={'project':'Atise Product Lab','description':'Explore a compact component that explains whether a brief, delivery and settlement reference have been verified.',
                          'deliverables':'Desktop and mobile component states with accessibility notes.','category':'Design',
                          'budget':400,'deadline':deadline,'status':'open','demo':False})

        self.stdout.write(self.style.SUCCESS('Local showcase ready.'))
        self.stdout.write(f'Credentials: {credentials_path}')

    @staticmethod
    def _password():
        return f'Push-{secrets.token_urlsafe(14)}-9!'
