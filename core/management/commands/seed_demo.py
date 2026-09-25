from datetime import timedelta
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from core.models import User, Job

class Command(BaseCommand):
    help='Add clearly labelled, non-actionable sample briefs. Never creates login credentials.'
    def handle(self,*args,**options):
        if settings.PRODUCTION: raise CommandError('Sample seeding is disabled in production.')
        user,created=User.objects.get_or_create(username='sample-editor@example.invalid',defaults={'email':'sample-editor@example.invalid','display_name':'Sample project','email_verified':False,'is_active':False})
        if created: user.set_unusable_password();user.save()
        samples=[('Design','Design an onboarding flow','Northstar Studio',600,'Help a small Web3 team make its first five minutes feel effortless. Map the journey from arrival to a complete profile.','A five-screen desktop flow, a mobile adaptation, and handover notes.'),('Content','Tell the story behind the product','Field Notes Collective',250,'Turn a technical brief into a useful, readable introduction for a developer audience.','One 1,200-word article, a short social summary, and source links.'),('Engineering','Build a thoughtful documentation page','Open Work Lab',900,'Create an accessible documentation experience that helps new contributors find their first task.','A responsive documentation page, keyboard navigation and implementation notes.')]
        for category,title,project,budget,description,deliverables in samples:
            Job.objects.get_or_create(owner=user,title=title,demo=True,defaults={'project':project,'budget':budget,'description':description,'deliverables':deliverables,'category':category,'deadline':timezone.localdate()+timedelta(days=21)})
        self.stdout.write('Sample briefs ready. No sample account can sign in.')
