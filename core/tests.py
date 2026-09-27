import re
from decimal import Decimal
from datetime import timedelta
from unittest.mock import patch
from django.test import TestCase, Client, override_settings
from django.conf import settings
from django.urls import reverse
from django.core import mail, signing
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.utils import timezone
from .models import User, PendingRegistration, Job, Application, Assignment, Payment, Event, RateBucket, Dispute, AccountSanction, Submission, Notification, WaitlistApplication, Invitation
from .invitations import hash_invitation_code
from .stellar import StellarVerificationError, assignment_memo, payment_uri, valid_account_id, verify_payment

@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class WorkspaceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        accepted=timezone.now()
        cls.owner=User.objects.create_user(username='owner@example.test',email='owner@example.test',password='Independent-cobalt-732!',display_name='Hiring Account',email_verified=True,terms_version='2026-09-25.1',terms_accepted_at=accepted)
        cls.worker=User.objects.create_user(username='worker@example.test',email='worker@example.test',password='Independent-cobalt-732!',display_name='Worker',email_verified=True,terms_version='2026-09-25.1',terms_accepted_at=accepted)
        cls.outsider=User.objects.create_user(username='other@example.test',email='other@example.test',password='Independent-cobalt-732!',display_name='Other',email_verified=True,terms_version='2026-09-25.1',terms_accepted_at=accepted)
    def setUp(self):
        self.job=Job.objects.create(owner=self.owner,project='Test Project',title='Design a useful page',description='Brief',deliverables='One accessible page',category='UI/UX Design',budget=400,deadline=timezone.localdate()+timedelta(days=14),moderation_status='approved')
    def login_as(self,user): self.client.force_login(user)
    def make_assignment(self,status='awaiting_acceptance'):
        self.job.status='assigned';self.job.save()
        return Assignment.objects.create(job=self.job,worker=self.worker,scope=self.job.deliverables,budget=400,status=status)
    def action(self,item,action,**data):
        if action == 'accept': data.setdefault('accept_terms','on')
        return self.client.post(reverse('assignment_action',args=[item.pk]),{'action':action,**data})
    def grant_invitation(self,email,code='PUSH-ABCD1234-EFGH5678'):
        application=WaitlistApplication.objects.create(
            name='Invited Tester',email=email.lower(),role='Developer',intended_use='Test hiring',
            reason='I can complete the test script.',accepted_testing_terms=True,status='approved',
            reviewed_by=self.owner,reviewed_at=timezone.now(),
        )
        invitation=Invitation.objects.create(
            application=application,email=email.lower(),code_hash=hash_invitation_code(code),
            created_by=self.owner,expires_at=timezone.now()+timedelta(days=7),
        )
        self.assertRedirects(self.client.post(reverse('invite_redeem'),{'code':code}),reverse('register'))
        return invitation
    def test_public_and_auth_pages_render(self):
        health=self.client.get(reverse('health'))
        self.assertEqual(health.status_code,200)
        self.assertEqual(health.json(),{'ok':True,'service':'push','network':'stellar-testnet'})
        self.assertEqual(health['Cache-Control'],'no-store')
        for name in ['home','product','how_it_works','privacy','waitlist','invite_redeem','login','password_reset','password_reset_done','password_reset_complete']:
            with self.subTest(name=name): self.assertEqual(self.client.get(reverse(name)).status_code,200)
        self.assertRedirects(self.client.get(reverse('jobs')),f"{reverse('login')}?next={reverse('jobs')}")
        self.assertRedirects(self.client.get(reverse('register')),reverse('invite_redeem'))
        self.login_as(self.owner)
        for name in ['workspace','work','profile','job_create','wallet','payments','inbox','notifications','help']:
            with self.subTest(name=name): self.assertEqual(self.client.get(reverse(name)).status_code,200)
    def test_google_auth_visibility_matches_configuration(self):
        self.assertEqual(self.client.get(reverse('login')).context['google_auth_enabled'],settings.GOOGLE_AUTH_ENABLED)
        self.assertEqual(self.client.get('/accounts/google/login/').status_code,302 if settings.GOOGLE_AUTH_ENABLED else 404)
    def test_waitlist_is_public_and_staff_can_issue_one_time_invitation(self):
        response=self.client.post(reverse('waitlist'),{
            'name':'Ada Tester','email':'ADA@example.test','role':'Developer','skills':'Django',
            'intended_use':'Test the complete hiring flow.','reason':'I can report reproducible bugs.',
            'accepted_testing_terms':'on',
        })
        self.assertEqual(response.status_code,200)
        application=WaitlistApplication.objects.get(email='ada@example.test')
        self.assertEqual(application.status,'pending')
        self.owner.is_staff=True;self.owner.save(update_fields=['is_staff']);self.login_as(self.owner)
        response=self.client.post(reverse('review_waitlist',args=[application.pk]),{'decision':'approve'})
        self.assertRedirects(response,reverse('moderation'))
        application.refresh_from_db();self.assertEqual(application.status,'approved')
        invitation=application.invitations.get();self.assertIsNone(invitation.used_at)
        self.assertEqual(len(mail.outbox),1);self.assertIn('Invitation code:',mail.outbox[0].body)
    def test_invitation_is_email_bound_and_registration_is_closed_without_it(self):
        self.assertRedirects(self.client.get(reverse('register')),reverse('invite_redeem'))
        self.grant_invitation('approved@example.test')
        response=self.client.post(reverse('register'),{
            'display_name':'Wrong Person','email':'wrong@example.test',
            'password1':'Long-example-password-723!','password2':'Long-example-password-723!','accept_terms':'on',
        })
        self.assertContains(response,'Use the approved email address')
        self.assertFalse(PendingRegistration.objects.filter(email='wrong@example.test').exists())
    def test_reapplying_revokes_an_earlier_unused_invitation(self):
        invitation=self.grant_invitation('again@example.test')
        self.client.post(reverse('waitlist'),{
            'name':'Again Tester','email':'again@example.test','role':'Developer','skills':'QA',
            'intended_use':'Run the workflow again.','reason':'I can retest regressions.',
            'accepted_testing_terms':'on',
        })
        invitation.refresh_from_db()
        self.assertIsNotNone(invitation.revoked_at)
        self.assertEqual(WaitlistApplication.objects.get(email='again@example.test').status,'pending')
    def test_register_verify_and_replay(self):
        invitation=self.grant_invitation('new@example.test')
        response=self.client.post(reverse('register'),{'display_name':'New Person','email':'New@Example.test','password1':'Long-example-password-723!','password2':'Long-example-password-723!','accept_terms':'on'})
        self.assertRedirects(response,reverse('verify_registration'))
        self.assertFalse(User.objects.filter(email='new@example.test').exists())
        pending=PendingRegistration.objects.get(email='new@example.test')
        self.assertNotEqual(pending.password_hash,'Long-example-password-723!')
        code=re.search(r'\b(\d{6})\b',mail.outbox[0].body).group(1)
        self.assertEqual(self.client.get(reverse('verify_registration')).status_code,200)
        self.assertEqual(self.client.post(reverse('verify_registration'),{'code':code}).status_code,302)
        user=User.objects.get(email='new@example.test')
        user.refresh_from_db();self.assertTrue(user.email_verified)
        invitation.refresh_from_db();self.assertEqual(invitation.used_by,user);self.assertIsNotNone(invitation.used_at)
        self.assertFalse(PendingRegistration.objects.filter(email='new@example.test').exists())
        self.assertRedirects(self.client.post(reverse('verify_registration'),{'code':code}),reverse('workspace'))
    def test_registration_explains_weak_password_and_existing_email(self):
        self.grant_invitation('atise@example.test')
        weak=self.client.post(reverse('register'),{'display_name':'Atise','email':'atise@example.test','password1':'password','password2':'password'})
        self.assertContains(weak,'at least 12 characters')
        self.assertContains(weak,'too common')
        self.client.get(reverse('invite_redeem'));self.grant_invitation('owner@example.test','PUSH-11112222-33334444')
        duplicate=self.client.post(reverse('register'),{'display_name':'Owner','email':'OWNER@EXAMPLE.TEST','password1':'Independent-cobalt-732!','password2':'Independent-cobalt-732!'})
        self.assertContains(duplicate,'An account already uses this email')
    def test_verification_rejects_forgery(self):
        self.assertEqual(self.client.post('/verify/not-a-valid-signature/').status_code,400)
    def test_email_case_deduplication(self):
        self.grant_invitation('owner@example.test')
        response=self.client.post(reverse('register'),{'display_name':'Fake','email':'OWNER@EXAMPLE.TEST','password1':'Long-example-password-723!','password2':'Long-example-password-723!'})
        self.assertEqual(response.status_code,200)
        self.assertEqual(User.objects.filter(email__iexact=self.owner.email).count(),1)
    def test_unverified_cannot_publish(self):
        self.worker.email_verified=False;self.worker.save();self.login_as(self.worker)
        self.assertRedirects(self.client.post(reverse('job_create'),{}),reverse('verify_email'))

    def test_safe_job_publishes_immediately_and_is_searchable_by_another_user(self):
        self.login_as(self.owner)
        data={'project':'Lantern Studio','title':'Edit four product videos','category':'Video Editing',
              'description':'Create four concise launch videos for our product page.',
              'deliverables':'Four MP4 files and editable project files.',
              'acceptance_criteria':'Each video is 30 seconds, captioned, and exported at 1080p.',
              'budget':450,'deadline':timezone.localdate()+timedelta(days=10),'revision_limit':2,'response_days':3}
        response=self.client.post(reverse('job_create'),data)
        self.assertEqual(response.status_code,302)
        job=Job.objects.get(title='Edit four product videos')
        self.assertEqual(job.moderation_status,'approved')

        self.login_as(self.outsider)
        results=self.client.get(reverse('jobs'),{'q':'Lantern Studio'})
        self.assertContains(results,'Edit four product videos')
        self.assertContains(results,'1 job')
        self.assertIn('no-store',results['Cache-Control'])
        detail=self.client.get(reverse('job_detail',args=[job.pk]))
        self.assertContains(detail,'data-copy-target')
        self.assertContains(detail,'Copy job link')
        self.assertContains(detail,reverse('job_detail',args=[job.pk]))

    def test_workspace_greeting_uses_the_current_weekday(self):
        self.owner.date_joined=timezone.now()-timedelta(days=2)
        self.owner.save(update_fields=['date_joined'])
        self.login_as(self.owner)
        response=self.client.get(reverse('workspace'))
        self.assertContains(response,f'Good {timezone.localdate().strftime("%A")},')

    def test_unverified_wallet_redirects_to_code_screen(self):
        self.worker.email_verified=False;self.worker.save();self.login_as(self.worker)
        self.assertRedirects(self.client.get(reverse('wallet')),reverse('verify_email'))

    def test_incorrect_verification_code_does_not_unlock_account(self):
        self.worker.email_verified=False;self.worker.save();self.login_as(self.worker)
        self.client.post(reverse('resend'))
        response=self.client.post(reverse('verify_email'),{'code':'000000'})
        self.assertContains(response,'That code is incorrect')
        self.worker.refresh_from_db();self.assertFalse(self.worker.email_verified)
    def test_private_routes_redirect_signed_out_visitors(self):
        application=Application.objects.create(job=self.job,worker=self.worker,proposal='Private proposal')
        assignment=self.make_assignment()
        private_urls=[reverse('workspace'),reverse('profile'),reverse('jobs'),reverse('job_detail',args=[self.job.pk]),reverse('job_create'),
                      reverse('job_edit',args=[self.job.pk]),reverse('apply',args=[self.job.pk]),
                      reverse('select',args=[application.pk]),reverse('assignment',args=[assignment.pk]),
                      reverse('assignment_action',args=[assignment.pk]),reverse('job_close',args=[self.job.pk]),
                      reverse('withdraw',args=[application.pk])]
        for url in private_urls:
            with self.subTest(url=url):
                response=self.client.get(url) if url in [reverse('workspace'),reverse('profile'),reverse('jobs'),reverse('job_detail',args=[self.job.pk]),reverse('job_create'),reverse('job_edit',args=[self.job.pk]),reverse('assignment',args=[assignment.pk])] else self.client.post(url)
                self.assertEqual(response.status_code,302)
                self.assertTrue(response.url.startswith(reverse('login')+'?next='))
    def test_csrf_and_logout_invalidate_session(self):
        c=Client(enforce_csrf_checks=True);c.force_login(self.worker)
        old_session=c.cookies['sessionid'].value
        self.assertEqual(c.post(reverse('logout')).status_code,403)
        c.get(reverse('profile'));credential=c.cookies['csrftoken'].value
        self.assertEqual(c.post(reverse('logout'),{'csrfmiddlewaretoken':credential}).status_code,302)
        attacker=Client();attacker.cookies['sessionid']=old_session
        self.assertEqual(attacker.get(reverse('workspace')).status_code,302)
        self.assertEqual(c.get(reverse('logout')).status_code,405)
    def test_email_login_case_and_unsafe_redirect(self):
        response=self.client.post(reverse('login'),{'username':'WORKER@EXAMPLE.TEST','password':'Independent-cobalt-732!','next':'https://attacker.invalid'})
        self.assertRedirects(response,reverse('workspace'))
    def test_login_rate_limit(self):
        for _ in range(12): self.client.post(reverse('login'),{'username':'absent@example.test','password':'wrong'})
        self.assertEqual(self.client.post(reverse('login'),{}).status_code,429)
    def test_profile_private_and_prevents_privilege_escalation(self):
        self.assertEqual(self.client.get(reverse('public_profile',args=[self.worker.pk])).status_code,404)
        self.login_as(self.worker)
        self.client.post(reverse('profile'),{'display_name':'Worker','bio':'<script>alert(1)</script>','skills':'Design','portfolio':'https://example.com','public_profile':'on','is_staff':'true','is_superuser':'true','email_verified':'true','email':'attacker@example.test'})
        self.worker.refresh_from_db()
        self.assertFalse(self.worker.is_staff);self.assertFalse(self.worker.is_superuser)
        self.assertEqual(self.worker.email,'worker@example.test')
        c=Client();response=c.get(reverse('public_profile',args=[self.worker.pk]))
        self.assertContains(response,'&lt;script&gt;');self.assertNotContains(response,'<script>')
        self.assertNotContains(response,self.worker.email)
    def test_unsafe_portfolio_rejected(self):
        self.login_as(self.worker)
        response=self.client.post(reverse('profile'),{'display_name':'Worker','portfolio':'javascript:alert(1)'})
        self.assertEqual(response.status_code,200)
        self.worker.refresh_from_db();self.assertEqual(self.worker.portfolio,'')

    def test_profile_photo_and_resume_are_database_backed_and_privacy_scoped(self):
        self.login_as(self.worker)
        image=SimpleUploadedFile('portrait.png',b'\x89PNG\r\n\x1a\n'+b'profile-image',content_type='image/png')
        resume=SimpleUploadedFile('worker-resume.pdf',b'%PDF-1.4\nresume',content_type='application/pdf')
        response=self.client.post(reverse('profile'),{
            'display_name':'Worker','bio':'Product designer','skills':'Design','portfolio':'',
            'stellar_address':'','profile_image':image,'resume_file':resume,
        })
        self.assertRedirects(response,reverse('profile'))
        self.worker.refresh_from_db()
        self.assertEqual(bytes(self.worker.profile_image),b'\x89PNG\r\n\x1a\nprofile-image')
        self.assertEqual(self.worker.profile_image_content_type,'image/png')
        self.assertEqual(self.worker.resume_filename,'worker-resume.pdf')

        outsider=Client()
        self.assertEqual(outsider.get(reverse('profile_image',args=[self.worker.pk])).status_code,404)
        self.assertEqual(outsider.get(reverse('resume_download',args=[self.worker.pk])).status_code,404)
        self.assertEqual(self.client.get(reverse('profile_image',args=[self.worker.pk])).status_code,200)
        self.worker.public_profile=True;self.worker.save(update_fields=['public_profile'])
        self.assertEqual(outsider.get(reverse('profile_image',args=[self.worker.pk])).status_code,200)
        download=outsider.get(reverse('resume_download',args=[self.worker.pk]))
        self.assertEqual(download.status_code,200)
        self.assertEqual(download['Content-Type'],'application/pdf')
        self.assertIn('attachment',download['Content-Disposition'])
        self.assertContains(outsider.get(reverse('public_profile',args=[self.worker.pk])),'Download résumé')

    def test_profile_rejects_disguised_uploads(self):
        self.login_as(self.worker)
        response=self.client.post(reverse('profile'),{
            'display_name':'Worker','bio':'','skills':'','portfolio':'','stellar_address':'',
            'profile_image':SimpleUploadedFile('fake.png',b'not-an-image',content_type='image/png'),
            'resume_file':SimpleUploadedFile('fake.pdf',b'not-a-pdf',content_type='application/pdf'),
        })
        self.assertEqual(response.status_code,200)
        self.assertContains(response,'Upload a valid JPG, PNG or WebP image')
        self.assertContains(response,'Upload a valid PDF résumé')
    def test_applications_private_and_duplicate_prevented(self):
        self.login_as(self.worker)
        url=reverse('apply',args=[self.job.pk])
        self.client.post(url,{'proposal':'Private proposal example'})
        self.client.post(url,{'proposal':'Duplicate'})
        self.assertEqual(Application.objects.count(),1)
        self.login_as(self.outsider)
        self.assertNotContains(self.client.get(reverse('job_detail',args=[self.job.pk])),'Private proposal example')
        self.login_as(self.owner)
        self.assertContains(self.client.get(reverse('job_detail',args=[self.job.pk])),'Private proposal example')
        self.assertEqual(self.client.post(url,{'proposal':'Own job'}).status_code,403)
    def test_only_owner_can_select_and_cannot_select_twice(self):
        app=Application.objects.create(job=self.job,worker=self.worker,proposal='My work')
        self.login_as(self.outsider)
        self.assertEqual(self.client.post(reverse('select',args=[app.pk])).status_code,404)
        self.login_as(self.owner)
        self.assertEqual(self.client.post(reverse('select',args=[app.pk])).status_code,302)
        self.assertEqual(self.client.post(reverse('select',args=[app.pk])).status_code,409)
        self.assertEqual(Assignment.objects.count(),1)
    def test_outsider_cannot_read_or_change_assignment(self):
        item=self.make_assignment();self.login_as(self.outsider)
        self.assertEqual(self.client.get(reverse('assignment',args=[item.pk])).status_code,404)
        self.assertEqual(self.action(item,'accept').status_code,404)
    def test_assignment_messages_are_participant_only(self):
        item=self.make_assignment('funded')
        url=reverse('assignment_message',args=[item.pk])
        self.login_as(self.worker);self.assertEqual(self.client.post(url,{'body':'The first draft is ready.'}).status_code,302)
        self.assertEqual(item.messages.count(),1)
        self.login_as(self.owner);self.assertContains(self.client.get(reverse('assignment',args=[item.pk])),'The first draft is ready.')
        self.login_as(self.outsider);self.assertEqual(self.client.post(url,{'body':'Intrusion'}).status_code,404)
        self.assertEqual(item.messages.count(),1)
        self.assertEqual(self.client.get(reverse('conversation',args=[item.pk])).status_code,404)
        self.login_as(self.worker)
        self.assertContains(self.client.get(reverse('inbox')),'Design a useful page')
        self.assertEqual(self.client.post(reverse('conversation',args=[item.pk]),{'body':'A second private message.'}).status_code,302)
        self.assertEqual(item.messages.count(),2)
    def test_wallet_request_is_non_custodial(self):
        self.login_as(self.worker)
        address='GBBD47IF6LWK7P7MDEVSCWR7DPUWV3NY3DTQEVFL4NAT4AQH3ZLLFLA5'
        response=self.client.post(reverse('wallet'),{'destination':address,'asset':'USDC','amount':'1.5','memo':'Push test'})
        self.assertEqual(response.status_code,200)
        self.assertTrue(response.context['request_uri'].startswith('web+stellar:pay?'))
        self.assertEqual(Payment.objects.count(),0)

    def test_wallet_resolves_member_email_and_supports_native_xlm(self):
        address='GBBD47IF6LWK7P7MDEVSCWR7DPUWV3NY3DTQEVFL4NAT4AQH3ZLLFLA5'
        self.owner.stellar_address=address;self.owner.save(update_fields=['stellar_address'])
        self.login_as(self.worker)
        response=self.client.post(reverse('wallet'),{
            'destination':self.owner.email.upper(),'asset':'XLM','amount':'2.5','memo':'Push test',
        })
        self.assertEqual(response.status_code,200)
        uri=response.context['request_uri']
        self.assertIn('destination='+address,uri)
        self.assertNotIn('asset_code',uri)
        self.assertEqual(Payment.objects.count(),0)

    @patch('core.views.account_balances')
    def test_wallet_displays_live_testnet_balances(self, balances):
        address='GBBD47IF6LWK7P7MDEVSCWR7DPUWV3NY3DTQEVFL4NAT4AQH3ZLLFLA5'
        self.worker.stellar_address=address;self.worker.save(update_fields=['stellar_address'])
        balances.return_value={'xlm':Decimal('9999.5000000'),'usdc':Decimal('25.0000000'),'has_usdc_trustline':True}
        self.login_as(self.worker)
        response=self.client.get(reverse('wallet'))
        self.assertContains(response,'9999.50 XLM')
        self.assertContains(response,'25.00 USDC')
        balances.assert_called_once_with(address)
    def test_freighter_connect_accepts_only_valid_testnet_public_address(self):
        address='GBBD47IF6LWK7P7MDEVSCWR7DPUWV3NY3DTQEVFL4NAT4AQH3ZLLFLA5'
        url=reverse('wallet_connect')
        self.assertEqual(self.client.post(url,data='{}',content_type='application/json').status_code,302)
        self.login_as(self.worker)
        wrong_network=self.client.post(url,data={'address':address,'network':'PUBLIC'},content_type='application/json')
        self.assertEqual(wrong_network.status_code,400)
        invalid=self.client.post(url,data={'address':address[:-1]+'A','network':'TESTNET'},content_type='application/json')
        self.assertEqual(invalid.status_code,400)
        connected=self.client.post(url,data={'address':address,'network':'TESTNET'},content_type='application/json')
        self.assertEqual(connected.status_code,200)
        self.worker.refresh_from_db()
        self.assertEqual(self.worker.stellar_address,address)
    def test_both_payment_simulations_and_immutable_amount(self):
        for method in ['usdc','bank_card']:
            with self.subTest(method=method):
                if Assignment.objects.exists():
                    self.job=Job.objects.create(owner=self.owner,project='Test',title='Second brief',description='Brief',deliverables='A deliverable',category='Design',budget=400,deadline=timezone.localdate()+timedelta(days=7))
                item=self.make_assignment()
                self.login_as(self.worker);self.assertEqual(self.action(item,'accept').status_code,302)
                self.assertEqual(self.action(item,'fund',payment_method=method).status_code,403)
                self.login_as(self.owner);self.assertEqual(self.action(item,'fund',payment_method=method,amount='1').status_code,302)
                self.login_as(self.worker);self.assertEqual(self.action(item,'submit',notes='Completed the scope',link='https://example.com/work').status_code,302)
                self.assertEqual(self.action(item,'approve').status_code,403)
                self.login_as(self.owner);self.assertEqual(self.action(item,'approve',amount='1',recipient=str(self.outsider.pk)).status_code,302)
                self.assertEqual(self.action(item,'approve').status_code,409)
                payment=Payment.objects.get(assignment=item)
                self.assertEqual(payment.amount,400);self.assertEqual(payment.method,method);self.assertTrue(payment.simulated)
                self.assertEqual(item.events.filter(kind='approve').count(),1)

    @patch('core.views.verify_payment')
    def test_stellar_testnet_payment_is_verified_before_completion(self,verify):
        address='GBBD47IF6LWK7P7MDEVSCWR7DPUWV3NY3DTQEVFL4NAT4AQH3ZLLFLA5'
        transaction_hash='a'*64
        self.worker.stellar_address=address;self.worker.save(update_fields=['stellar_address'])
        item=self.make_assignment('submitted')
        item.payment_method='stellar_usdc_testnet';item.save(update_fields=['payment_method'])
        verify.return_value=transaction_hash
        self.login_as(self.owner)
        self.assertEqual(self.action(item,'approve',transaction_hash=transaction_hash).status_code,302)
        verify.assert_called_once_with(transaction_hash=transaction_hash,destination=address,amount=400,memo=assignment_memo(item.id))
        payment=Payment.objects.get(assignment=item)
        self.assertFalse(payment.simulated)
        self.assertEqual(payment.network,'stellar_testnet')
        self.assertEqual(payment.transaction_hash,transaction_hash)

    def test_stellar_payment_requires_worker_address_and_transaction_hash(self):
        item=self.make_assignment('awaiting_funding');self.login_as(self.owner)
        self.assertEqual(self.action(item,'fund',payment_method='stellar_usdc_testnet').status_code,400)
        self.worker.stellar_address='GBBD47IF6LWK7P7MDEVSCWR7DPUWV3NY3DTQEVFL4NAT4AQH3ZLLFLA5';self.worker.save()
        item.status='submitted';item.payment_method='stellar_usdc_testnet';item.save()
        self.assertEqual(self.action(item,'approve').status_code,400)
        self.assertFalse(Payment.objects.exists())

    @patch('core.stellar._get_json')
    def test_stellar_verifier_checks_reference_asset_recipient_and_amount(self,get_json):
        address='GBBD47IF6LWK7P7MDEVSCWR7DPUWV3NY3DTQEVFL4NAT4AQH3ZLLFLA5'
        memo='push-example'
        get_json.side_effect=[
            {'successful':True,'memo_type':'text','memo':memo},
            {'_embedded':{'records':[{'type':'payment','to':address,'asset_code':'USDC',
                'asset_issuer':address,'amount':'400.0000000'}]}},
        ]
        self.assertEqual(verify_payment(transaction_hash='b'*64,destination=address,amount=400,memo=memo),'b'*64)
        get_json.side_effect=[
            {'successful':True,'memo_type':'text','memo':'wrong'},
            {'_embedded':{'records':[]}},
        ]
        with self.assertRaises(StellarVerificationError):
            verify_payment(transaction_hash='c'*64,destination=address,amount=400,memo=memo)

    def test_stellar_payment_uri_contains_no_secret(self):
        address='GBBD47IF6LWK7P7MDEVSCWR7DPUWV3NY3DTQEVFL4NAT4AQH3ZLLFLA5'
        uri=payment_uri(destination=address,amount=400,memo='push-example')
        self.assertTrue(uri.startswith('web+stellar:pay?'))
        self.assertIn('destination='+address,uri)
        self.assertNotIn('secret',uri.lower())

    def test_stellar_public_address_checksum_is_validated(self):
        address='GBBD47IF6LWK7P7MDEVSCWR7DPUWV3NY3DTQEVFL4NAT4AQH3ZLLFLA5'
        self.assertTrue(valid_account_id(address))
        self.assertFalse(valid_account_id(address[:-1]+'A'))
    def test_dispute_blocks_release(self):
        item=self.make_assignment('submitted');self.login_as(self.worker)
        self.assertEqual(self.action(item,'dispute',note='Scope disagreement').status_code,302)
        self.login_as(self.owner);self.assertEqual(self.action(item,'approve').status_code,409)
        self.assertFalse(Payment.objects.exists())
    def test_revision_and_cancel_rules(self):
        item=self.make_assignment('submitted');self.login_as(self.owner)
        self.assertEqual(self.action(item,'revise').status_code,400)
        self.assertEqual(self.action(item,'revise',note='Please include the missing export').status_code,302)
        item.refresh_from_db();self.assertEqual(item.status,'funded')
        self.assertEqual(self.action(item,'cancel').status_code,403)
    def test_invalid_submission_does_not_advance(self):
        item=self.make_assignment('funded');self.login_as(self.worker)
        self.assertEqual(self.action(item,'submit',notes='Here',link='javascript:bad()').status_code,400)
        item.refresh_from_db();self.assertEqual(item.status,'funded')
    def test_security_headers_and_private_cache(self):
        self.login_as(self.worker);response=self.client.get(reverse('workspace'))
        self.assertEqual(response['X-Frame-Options'],'DENY')
        self.assertIn('no-store',response['Cache-Control'])
        self.assertIn("script-src 'self'",response['Content-Security-Policy'])
        self.assertNotIn("'unsafe-inline'",response['Content-Security-Policy'])
    def test_password_reset_single_use_and_revokes_old_session(self):
        self.login_as(self.worker)
        old_session=self.client.cookies['sessionid'].value
        self.client.logout()
        self.client.post(reverse('password_reset'),{'email':self.worker.email})
        self.assertEqual(len(mail.outbox),1)
        credential=default_token_generator.make_token(self.worker)
        uid=urlsafe_base64_encode(force_bytes(self.worker.pk))
        link=reverse('password_reset_confirm',args=[uid,credential])
        response=self.client.get(link)
        reset_page=response.url
        self.assertEqual(self.client.get(reset_page).status_code,200)
        response=self.client.post(reset_page,{'new_password1':'Another-strong-password-847!','new_password2':'Another-strong-password-847!'})
        self.assertRedirects(response,reverse('password_reset_complete'))
        self.worker.refresh_from_db();self.assertTrue(self.worker.check_password('Another-strong-password-847!'))
        self.assertFalse(default_token_generator.check_token(self.worker,credential))
        attacker=Client();attacker.cookies['sessionid']=old_session
        self.assertEqual(attacker.get(reverse('workspace')).status_code,302)

    def test_password_reset_emails_google_only_account(self):
        google_user=User.objects.create_user(
            username='google-only@example.test',
            email='google-only@example.test',
            display_name='Google Account',
            email_verified=True,
        )
        google_user.set_unusable_password()
        google_user.save(update_fields=['password'])
        response=self.client.post(reverse('password_reset'),{'email':'GOOGLE-ONLY@example.test'})
        self.assertRedirects(response,reverse('password_reset_done'))
        self.assertEqual(len(mail.outbox),1)
        self.assertIn('/reset/',mail.outbox[0].body)
    def test_sample_jobs_not_actionable(self):
        self.job.demo=True;self.job.save();self.login_as(self.worker)
        self.assertEqual(self.client.post(reverse('apply',args=[self.job.pk]),{'proposal':'Test'}).status_code,400)

    def test_close_job_owner_only_and_blocks_new_work(self):
        application=Application.objects.create(job=self.job,worker=self.worker,proposal='Preserved proposal')
        url=reverse('job_close',args=[self.job.pk])
        self.login_as(self.outsider)
        self.assertEqual(self.client.post(url).status_code,404)
        self.login_as(self.owner)
        self.assertEqual(self.client.get(url).status_code,405)
        self.assertEqual(self.client.post(url).status_code,302)
        self.job.refresh_from_db();self.assertEqual(self.job.status,'closed')
        self.assertEqual(self.client.post(url).status_code,409)
        self.assertEqual(self.client.post(reverse('select',args=[application.pk])).status_code,409)
        self.assertContains(self.client.get(reverse('job_detail',args=[self.job.pk])),'Preserved proposal')
        self.login_as(self.outsider)
        self.assertEqual(self.client.post(reverse('apply',args=[self.job.pk]),{'proposal':'Late'}).status_code,400)
        self.assertFalse(Assignment.objects.exists())

    def test_withdraw_private_retained_and_cannot_select_or_reapply(self):
        application=Application.objects.create(job=self.job,worker=self.worker,proposal='Private retained proposal')
        url=reverse('withdraw',args=[application.pk])
        for person in [self.outsider,self.owner]:
            self.login_as(person);self.assertEqual(self.client.post(url).status_code,404)
        self.login_as(self.worker)
        self.assertEqual(self.client.get(url).status_code,405)
        self.assertEqual(self.client.post(url).status_code,302)
        self.assertEqual(self.client.post(url).status_code,409)
        application.refresh_from_db();self.assertTrue(application.withdrawn)
        self.assertEqual(application.proposal,'Private retained proposal')
        self.assertContains(self.client.get(reverse('workspace')),'Withdrawn')
        self.client.post(reverse('apply',args=[self.job.pk]),{'proposal':'Try again'})
        self.assertEqual(Application.objects.filter(job=self.job,worker=self.worker).count(),1)
        self.login_as(self.owner)
        self.assertEqual(self.client.post(reverse('select',args=[application.pk])).status_code,409)
        self.job.refresh_from_db();self.assertEqual(self.job.status,'open')
        self.assertFalse(Assignment.objects.exists())
        self.login_as(self.outsider)
        self.assertNotContains(self.client.get(reverse('job_detail',args=[self.job.pk])),'Private retained proposal')

    def test_close_and_withdraw_do_not_bypass_assignment(self):
        application=Application.objects.create(job=self.job,worker=self.worker,proposal='Selected')
        self.login_as(self.owner)
        self.client.post(reverse('select',args=[application.pk]))
        self.assertEqual(self.client.post(reverse('job_close',args=[self.job.pk])).status_code,409)
        self.login_as(self.worker)
        self.assertEqual(self.client.post(reverse('withdraw',args=[application.pk])).status_code,409)
        application.refresh_from_db();self.assertFalse(application.withdrawn)
        self.assertEqual(Assignment.objects.get(job=self.job).status,'awaiting_acceptance')

    def test_close_and_withdraw_require_csrf(self):
        application=Application.objects.create(job=self.job,worker=self.worker,proposal='Proposal')
        client=Client(enforce_csrf_checks=True)
        client.force_login(self.owner)
        self.assertEqual(client.post(reverse('job_close',args=[self.job.pk])).status_code,403)
        client.force_login(self.worker)
        self.assertEqual(client.post(reverse('withdraw',args=[application.pk])).status_code,403)

    def test_owner_can_edit_only_before_first_application(self):
        url=reverse('job_edit',args=[self.job.pk])
        self.login_as(self.outsider)
        self.assertEqual(self.client.get(url).status_code,404)
        self.login_as(self.owner)
        self.assertEqual(self.client.get(url).status_code,200)
        data={'project':'Updated project','title':'Updated title','category':'Web Development',
              'description':'Updated description','deliverables':'Updated deliverable',
              'budget':725,'deadline':timezone.localdate()+timedelta(days=30)}
        self.assertEqual(self.client.post(url,data).status_code,302)
        self.job.refresh_from_db()
        self.assertEqual(self.job.title,'Updated title')
        self.assertEqual(self.job.budget,725)
        Application.objects.create(job=self.job,worker=self.worker,proposal='Terms considered')
        self.assertEqual(self.client.get(url).status_code,409)
        data['title']='Silent change'
        self.assertEqual(self.client.post(url,data).status_code,409)
        self.job.refresh_from_db();self.assertEqual(self.job.title,'Updated title')

    def test_sample_closed_and_assigned_jobs_cannot_be_edited(self):
        url=reverse('job_edit',args=[self.job.pk])
        self.login_as(self.owner)
        self.job.demo=True;self.job.save()
        self.assertEqual(self.client.get(url).status_code,404)
        self.job.demo=False;self.job.status='closed';self.job.save()
        self.assertEqual(self.client.get(url).status_code,409)
        self.job.status='assigned';self.job.save()
        self.assertEqual(self.client.get(url).status_code,409)

    def test_selection_creates_immutable_agreement_snapshot(self):
        self.job.acceptance_criteria='Desktop and mobile layouts pass the checklist.'
        self.job.revision_limit=3;self.job.response_days=4;self.job.save()
        application=Application.objects.create(job=self.job,worker=self.worker,proposal='Ready')
        self.login_as(self.owner);self.client.post(reverse('select',args=[application.pk]))
        item=Assignment.objects.get(job=self.job)
        self.assertEqual(item.agreement_snapshot['acceptance_criteria'],self.job.acceptance_criteria)
        self.assertEqual(item.agreement_snapshot['budget'],400)
        self.job.deliverables='Changed later';self.job.save(update_fields=['deliverables'])
        item.refresh_from_db();self.assertEqual(item.agreement_snapshot['deliverables'],'One accessible page')

    def test_delivery_sets_client_deadline_and_preserves_evidence(self):
        item=self.make_assignment('funded');self.login_as(self.worker)
        response=self.action(item,'submit',notes='Finished',link='https://example.com/work',evidence='Export checklist and repository tag v1.')
        self.assertEqual(response.status_code,302)
        item.refresh_from_db();self.assertIsNotNone(item.client_response_due)
        self.assertGreater(item.client_response_due,timezone.now()+timedelta(days=2))
        self.assertEqual(Submission.objects.get(assignment=item).evidence,'Export checklist and repository tag v1.')

    def test_staff_can_resolve_dispute_with_simulated_split(self):
        item=self.make_assignment('submitted');item.payment_method='usdc';item.save()
        self.login_as(self.worker);self.action(item,'dispute',note='The delivery was rejected without reference to the criteria.')
        dispute=Dispute.objects.get(assignment=item)
        self.login_as(self.outsider)
        self.assertEqual(self.client.post(reverse('moderate_dispute',args=[dispute.pk]),{'resolution':'release','decision_note':'No'}).status_code,403)
        self.owner.is_staff=True;self.owner.save(update_fields=['is_staff']);self.login_as(self.owner)
        response=self.client.post(reverse('moderate_dispute',args=[dispute.pk]),{'resolution':'split','split_percent':60,'decision_note':'Both parties contributed to the missed handover.'})
        self.assertEqual(response.status_code,302)
        dispute.refresh_from_db();item.refresh_from_db()
        self.assertEqual(dispute.status,'resolved');self.assertEqual(item.status,'paid')
        payment=Payment.objects.get(assignment=item)
        self.assertEqual(payment.amount,240);self.assertTrue(payment.simulated)

    def test_flagged_listing_is_hidden_until_staff_approves(self):
        self.login_as(self.owner)
        data={'project':'Risky','title':'Fast work','category':'Graphic Design','description':'Contact by Telegram only and pay outside.',
              'deliverables':'One file','acceptance_criteria':'One valid file','budget':100,'deadline':timezone.localdate()+timedelta(days=7),
              'revision_limit':1,'response_days':3}
        response=self.client.post(reverse('job_create'),data);self.assertEqual(response.status_code,302)
        flagged=Job.objects.get(title='Fast work');self.assertEqual(flagged.moderation_status,'review')
        self.login_as(self.outsider);self.assertEqual(self.client.get(reverse('job_detail',args=[flagged.pk])).status_code,404)
        self.owner.is_staff=True;self.owner.save(update_fields=['is_staff']);self.login_as(self.owner)
        self.client.post(reverse('moderate_job',args=[flagged.pk]),{'decision':'approved'})
        flagged.refresh_from_db();self.assertEqual(flagged.moderation_status,'approved')

    def test_active_ban_blocks_verified_product_actions(self):
        AccountSanction.objects.create(user=self.worker,kind='ban',reason='Confirmed fraud test.',created_by=self.owner)
        self.login_as(self.worker)
        self.assertEqual(self.client.get(reverse('wallet')).status_code,403)

    def test_registration_requires_terms(self):
        self.grant_invitation('terms@example.test')
        data={'display_name':'Terms Test','email':'terms@example.test','password1':'Long-example-password-723!','password2':'Long-example-password-723!'}
        response=self.client.post(reverse('register'),data)
        self.assertEqual(response.status_code,200);self.assertContains(response,'This field is required')
        self.assertFalse(PendingRegistration.objects.filter(email='terms@example.test').exists())

    def test_revised_terms_require_fresh_acceptance(self):
        self.worker.terms_version='older-version';self.worker.save(update_fields=['terms_version']);self.login_as(self.worker)
        self.assertRedirects(self.client.get(reverse('work')),reverse('accept_terms'))
        response=self.client.post(reverse('accept_terms'),{'accept_terms':'on'})
        self.assertRedirects(response,reverse('workspace'))
        self.worker.refresh_from_db();self.assertEqual(self.worker.terms_version,'2026-09-25.1')

    def test_accepting_assignment_requires_explicit_agreement_confirmation(self):
        item=self.make_assignment();self.login_as(self.worker)
        response=self.client.post(reverse('assignment_action',args=[item.pk]),{'action':'accept'})
        self.assertEqual(response.status_code,400)
        item.refresh_from_db();self.assertEqual(item.status,'awaiting_acceptance');self.assertIsNone(item.accepted_terms_at)
        self.assertEqual(self.action(item,'accept').status_code,302)
        item.refresh_from_db();self.assertIsNotNone(item.accepted_terms_at)

    def test_message_notification_opens_conversation_and_marks_read(self):
        item=self.make_assignment('funded');self.login_as(self.worker)
        self.client.post(reverse('assignment_message',args=[item.pk]),{'body':'The draft is ready.'})
        notice=Notification.objects.get(recipient=self.owner,kind='message')
        self.assertIsNone(notice.read_at)
        self.login_as(self.owner);self.client.get(reverse('conversation',args=[item.pk]))
        notice.refresh_from_db();self.assertIsNotNone(notice.read_at)

    def test_work_page_groups_worker_and_hiring_records(self):
        item=self.make_assignment('funded');self.login_as(self.worker)
        response=self.client.get(reverse('work'));self.assertContains(response,'Assigned to me');self.assertContains(response,item.job.title)
        self.login_as(self.owner);response=self.client.get(reverse('work'));self.assertContains(response,'People I hired');self.assertContains(response,item.worker.display_name)

    def test_assigned_work_page_highlights_worker_actions(self):
        waiting=self.make_assignment('awaiting_acceptance')
        second_job=Job.objects.create(owner=self.owner,project='Second project',title='Deliver the final export',description='Brief',deliverables='Export',category='Video Editing',budget=250,deadline=timezone.localdate()+timedelta(days=7),moderation_status='approved')
        ready=Assignment.objects.create(job=second_job,worker=self.worker,scope='Export',budget=250,status='funded')
        self.login_as(self.worker)
        response=self.client.get(reverse('assigned_work'))
        self.assertContains(response,'Jobs I’m doing')
        self.assertContains(response,'Review and accept')
        self.assertContains(response,'Submit work')
        self.assertContains(response,reverse('assignment',args=[waiting.pk]))
        self.assertContains(response,reverse('assignment',args=[ready.pk]))

    def test_activity_status_reports_unread_and_work_counts(self):
        item=self.make_assignment('awaiting_acceptance')
        Notification.objects.create(recipient=self.worker,kind='selection',title='You were selected',body='Open the agreement.',link=reverse('assignment',args=[item.pk]))
        self.login_as(self.worker)
        response=self.client.get(reverse('activity_status'))
        self.assertEqual(response.status_code,200)
        self.assertIn('no-store',response['Cache-Control'])
        payload=response.json()
        self.assertEqual(payload['assigned'],1)
        self.assertEqual(payload['work_attention'],1)
        self.assertEqual(payload['notifications'],1)
        self.assertEqual(payload['latest']['title'],'You were selected')
