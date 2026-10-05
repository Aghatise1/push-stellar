import re
import json
from io import StringIO
from decimal import Decimal
from datetime import timedelta
from unittest.mock import patch
from django.test import TestCase, Client, RequestFactory, override_settings
from django.conf import settings
from django.urls import reverse
from django.core import mail, signing
from django.core.mail import EmailMessage
from django.core.management import call_command
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.utils import timezone
from stellar_sdk import Account, Asset, Keypair, Network, TransactionBuilder
from .models import AccountActivity, User, PendingRegistration, Job, Application, Assignment, Payment, WalletTransfer, Event, RateBucket, Dispute, AccountSanction, Submission, Notification, WaitlistApplication, Invitation, StaffAccess, SupportTicket, TicketFeedback, EmailDelivery, AuditEvent, DocumentationArticle, CommunityPost, CommunityReply, CommunityReport
from .invitations import hash_invitation_code
from .stellar import StellarVerificationError, assignment_memo, build_payment_xdr, payment_uri, prepare_payment, valid_account_id, validate_signed_payment, verify_payment
from .email_backend import BrevoEmailBackend

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
    def connect_wallet_session(self,address):
        session=self.client.session
        session['wallet_connected_address']=address
        session.save()
    def make_assignment(self,status='awaiting_acceptance'):
        self.job.status='assigned';self.job.save()
        return Assignment.objects.create(job=self.job,worker=self.worker,scope=self.job.deliverables,budget=400,status=status)
    def action(self,item,action,**data):
        if action == 'accept': data.setdefault('accept_terms','on')
        return self.client.post(reverse('assignment_action',args=[item.pk]),{'action':action,**data})
    def test_activity_counts_members_once_and_excludes_polling_and_staff(self):
        self.grant_staff(self.owner,'owner')
        self.login_as(self.worker)
        self.client.get(reverse('activity_status'))
        self.assertFalse(AccountActivity.objects.filter(user=self.worker).exists())
        self.client.get(reverse('account_settings'))
        self.client.get(reverse('account_settings'))
        self.assertEqual(AccountActivity.objects.filter(user=self.worker).count(),1)
        self.client.logout();self.login_as(self.owner)
        response=self.client.get(reverse('owner_dashboard'))
        self.assertNotContains(response,'ops-board')
        self.assertContains(response,'Choose a workspace')
        self.assertNotContains(response,'top-settings-link')
        response=self.client.get(reverse('operations_analytics'))
        report=response.context['report']
        self.assertEqual(report['member_total'],2)
        self.assertEqual(report['active_period'],1)
        self.assertEqual(report['rows'][-1]['registered'],2)
        self.assertEqual(report['rows'][-1]['active'],1)
        self.assertIsNone(report['rows'][0]['active'])
        self.assertEqual(report['common'][2]['value'],1)
        self.assertEqual(report['common'][3]['value'],1)

    def test_reporting_period_and_completion_dates_are_truthful(self):
        item=self.make_assignment('paid')
        payment=Payment.objects.create(assignment=item,amount=400,method='usdc')
        Payment.objects.filter(pk=payment.pk).update(created_at=timezone.now()-timedelta(days=10))
        self.grant_staff(self.owner,'admin');self.login_as(self.owner)
        short=self.client.get(reverse('operations_analytics')+'?days=7').context['report']
        month=self.client.get(reverse('operations_analytics')+'?days=30').context['report']
        self.assertEqual(short['series'][1]['total'],0)
        self.assertEqual(month['series'][1]['total'],1)
        self.assertEqual(month['finance']['simulated'],400)
        self.assertEqual(month['finance']['verified_testnet'],0)
        self.assertEqual(len(short['rows']),7)
        self.assertEqual(self.client.get(reverse('operations_analytics')+'?days=999999').context['report']['days'],30)

    def test_owner_report_preview_keeps_role_and_trust_support_cannot_escalate(self):
        self.grant_staff(self.owner,'owner');self.login_as(self.owner)
        response=self.client.get(reverse('operations_analytics')+'?view=trust_support&days=7')
        self.assertEqual(response.context['role'],'trust_support')
        self.assertNotContains(response,'Collected platform revenue')
        self.assertContains(response,'amp;view=trust_support')
        self.client.logout();self.grant_staff(self.worker,'trust_support');self.login_as(self.worker)
        self.assertEqual(self.client.get(reverse('operations_analytics')+'?view=owner').status_code,403)
        self.assertContains(self.client.get(reverse('operations_analytics')),'No ratings yet')

    def test_recovery_failure_is_logged_without_disclosing_account(self):
        with patch('core.mailer.send_mail',side_effect=TimeoutError):
            response=self.client.post(reverse('password_reset'),{'email':self.worker.email})
        self.assertEqual(response.status_code,302)
        self.assertTrue(EmailDelivery.objects.filter(category='password_recovery',status='failed',recipient=self.worker.email).exists())
        absent=self.client.post(reverse('password_reset'),{'email':'absent@example.test'})
        self.assertEqual(absent.status_code,response.status_code)
        self.assertEqual(absent.url,response.url)

    def test_auth_throttles_render_the_form_instead_of_plain_text(self):
        with patch('core.views.limited',return_value=True):
            for name in ['login','staff_login','password_reset']:
                response=self.client.post(reverse(name),{'email':self.worker.email,'username':self.worker.email,'password':'wrong'})
                self.assertContains(response,'Too many attempts',status_code=429)
                self.assertContains(response,'<form',status_code=429)

    def grant_staff(self,user,role='trust_support'):
        user.is_staff=True;user.save(update_fields=['is_staff'])
        return StaffAccess.objects.update_or_create(user=user,defaults={'role':role,'status':'approved','approved_at':timezone.now()})[0]
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
        self.assertRedirects(self.client.post(reverse('invite_redeem'),{'code':code}),reverse('verification_success'))
        return invitation
    def test_public_and_auth_pages_render(self):
        health=self.client.get(reverse('health'))
        self.assertEqual(health.status_code,200)
        self.assertEqual(health.json(),{'ok':True,'service':'push','network':'stellar-testnet'})
        self.assertEqual(health['Cache-Control'],'no-store')
        for name in ['home','product','how_it_works','privacy','documentation','waitlist','invite_redeem','login','password_reset','password_reset_done','password_reset_complete']:
            with self.subTest(name=name): self.assertEqual(self.client.get(reverse(name)).status_code,200)
        self.assertRedirects(self.client.get(reverse('jobs')),f"{reverse('login')}?next={reverse('jobs')}")
        self.assertRedirects(self.client.get(reverse('register')),reverse('invite_redeem'))
        self.login_as(self.owner)
        for name in ['workspace','work','profile','job_create','wallet','payments','inbox','notifications','help']:
            with self.subTest(name=name): self.assertEqual(self.client.get(reverse(name)).status_code,200)

    def test_community_requires_a_verified_member_and_creates_a_post(self):
        self.assertRedirects(self.client.get(reverse('community')),f"{reverse('login')}?next={reverse('community')}")
        self.login_as(self.owner)
        response=self.client.post(reverse('community_create'),{
            'topic':'stellar','title':'Build a Stellar testnet payment guide',
            'body':'Looking for a technical writer and a wallet tester.','skills':'Stellar, documentation',
        })
        post=CommunityPost.objects.get()
        self.assertRedirects(response,reverse('community_detail',args=[post.pk]))
        listing=self.client.get(reverse('community'))
        self.assertContains(listing,'Build a Stellar testnet payment guide')
        self.assertContains(listing,'Stellar builders')

    def test_community_search_reply_and_private_profile_rules(self):
        post=CommunityPost.objects.create(author=self.owner,topic='skills',title='Exchange research for design',body='I can research user needs.',skills='Research, UI design')
        self.login_as(self.worker)
        self.assertContains(self.client.get(reverse('community')+'?q=Research&topic=skills'),post.title)
        self.assertNotContains(self.client.get(reverse('community')+'?q=Python'),post.title)
        response=self.client.post(reverse('community_reply',args=[post.pk]),{'body':'I can help with interface design.'})
        self.assertRedirects(response,reverse('community_detail',args=[post.pk]))
        self.assertEqual(CommunityReply.objects.get().author,self.worker)
        detail=self.client.get(reverse('community_detail',args=[post.pk]))
        self.assertContains(detail,'I can help with interface design.')
        self.assertNotContains(detail,reverse('public_profile',args=[self.owner.pk]))
        self.assertTrue(Notification.objects.filter(recipient=self.owner,kind='community').exists())

    def test_community_content_is_escaped_and_closed_posts_reject_replies(self):
        self.login_as(self.owner)
        self.client.post(reverse('community_create'),{
            'topic':'question','title':'Safe question','body':'<script>alert(1)</script>','skills':'',
        })
        post=CommunityPost.objects.get()
        detail=self.client.get(reverse('community_detail',args=[post.pk]))
        self.assertContains(detail,'&lt;script&gt;alert(1)&lt;/script&gt;')
        self.client.post(reverse('community_close',args=[post.pk]))
        post.refresh_from_db();self.assertEqual(post.status,'closed')
        self.client.logout();self.login_as(self.worker)
        self.assertEqual(self.client.post(reverse('community_reply',args=[post.pk]),{'body':'Late reply'}).status_code,404)

    def test_community_reports_are_deduplicated_and_staff_can_remove_post(self):
        post=CommunityPost.objects.create(author=self.owner,topic='collaboration',title='Questionable request',body='A post to review.')
        self.login_as(self.worker)
        url=reverse('community_report',args=[post.pk])
        self.client.post(url,{'reason':'unsafe','detail':'Requests a credential.'})
        self.client.post(url,{'reason':'spam','detail':'Second attempt.'})
        self.assertEqual(CommunityReport.objects.filter(post=post,reporter=self.worker).count(),1)
        self.client.logout();self.grant_staff(self.outsider,'trust_support');self.login_as(self.outsider)
        desk=self.client.get(reverse('moderation'))
        self.assertContains(desk,'Questionable request')
        self.client.post(reverse('moderate_community_post',args=[post.pk]),{'action':'remove'})
        post.refresh_from_db();self.assertEqual(post.status,'removed')
        report=CommunityReport.objects.get();self.assertIsNotNone(report.resolved_at)
        self.client.logout();self.login_as(self.worker)
        self.assertEqual(self.client.get(reverse('community_detail',args=[post.pk])).status_code,404)

    @override_settings(PUSH_RELEASE='16464714ed3e')
    def test_health_reports_the_deployed_release_when_host_provides_it(self):
        self.assertEqual(self.client.get(reverse('health')).json()['release'],'16464714ed3e')
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
        self.grant_staff(self.owner);self.login_as(self.owner)
        response=self.client.post(reverse('review_waitlist',args=[application.pk]),{'decision':'approve'})
        self.assertRedirects(response,reverse('staff_invitations'))
        application.refresh_from_db();self.assertEqual(application.status,'approved')
        invitation=application.invitations.get();self.assertIsNone(invitation.used_at)
        self.assertEqual(len(mail.outbox),1);self.assertIn('Invitation code:',mail.outbox[0].body)
        delivery=EmailDelivery.objects.get(invitation=invitation)
        self.assertEqual(delivery.status,'sent')
        page=self.client.get(reverse('staff_invitations'))
        self.assertContains(page,'Tester applications')
        self.assertContains(page,'Ada Tester')
        self.assertContains(page,'Email accepted by provider')
        self.assertNotContains(self.client.get(reverse('moderation')),'Tester waitlist')

    def test_rejected_tester_stays_in_the_combined_invitation_workspace(self):
        application=WaitlistApplication.objects.create(
            name='Later Tester',email='later@example.test',role='QA',
            intended_use='Test later.',reason='Available next round.',accepted_testing_terms=True,
        )
        self.grant_staff(self.owner);self.login_as(self.owner)
        response=self.client.post(reverse('review_waitlist',args=[application.pk]),{'decision':'reject'})
        self.assertRedirects(response,reverse('staff_invitations'))
        application.refresh_from_db()
        self.assertEqual(application.status,'rejected')
        page=self.client.get(reverse('staff_invitations'))
        self.assertContains(page,'Later Tester')
        self.assertContains(page,'Rejected')
    def test_csrf_origins_include_only_the_allowlisted_render_service(self):
        from config.security import trusted_csrf_origins
        canonical='https://pushearn.xyz'
        alias='push-preview.onrender.com'
        self.assertEqual(trusted_csrf_origins(canonical,['pushearn.xyz',alias],alias),
                         [canonical,f'https://{alias}'])
        self.assertEqual(trusted_csrf_origins(canonical,['pushearn.xyz'],alias),[canonical])
        self.assertEqual(trusted_csrf_origins(canonical,['*.onrender.com'],'*.onrender.com'),[canonical])
        self.assertEqual(trusted_csrf_origins(canonical,['pushearn.xyz'],'pushearn.xyz'),[canonical])
        self.assertEqual(trusted_csrf_origins('http://localhost',['localhost'],''),[])

    @override_settings(DEBUG=False)
    def test_error_pages_are_branded_and_keep_their_status_codes(self):
        response=self.client.get('/this-page-does-not-exist/')
        self.assertContains(response,'Error 404',status_code=404)
        self.assertContains(response,'images/push-logo',status_code=404)
        self.assertContains(response,'error.css',status_code=404)
        self.assertEqual(response['Cache-Control'],'no-store, private')
        from .errors import bad_request, server_error
        request=RequestFactory().get('/')
        with self.assertNumQueries(0):
            self.assertContains(bad_request(request),'Error 400',status_code=400)
            self.assertContains(server_error(request),'Error 500',status_code=500)
        client=Client(enforce_csrf_checks=True)
        response=client.post(reverse('review_waitlist',args=[7]),{'decision':'approve'})
        self.assertContains(response,'Error 403',status_code=403)
        self.assertContains(response,'Your action was not submitted',status_code=403)
        self.assertContains(response,'href="/moderation/"',status_code=403)
        self.assertNotContains(response,'DEBUG=True',status_code=403)

    def test_plain_errors_are_branded_and_json_errors_remain_json(self):
        from django.http import HttpResponse, JsonResponse
        from .middleware import AppSecurityMiddleware
        request=RequestFactory().get('/')
        request.user=self.worker
        middleware=AppSecurityMiddleware(lambda request: HttpResponse('Try later.',status=429))
        response=middleware(request)
        self.assertContains(response,'Error 429',status_code=429)
        self.assertContains(response,'Try later.',status_code=429)
        self.assertEqual(response['Retry-After'],'900')
        middleware=AppSecurityMiddleware(lambda request: JsonResponse({'error':'Try later.'},status=429))
        self.assertEqual(json.loads(middleware(request).content),{'error':'Try later.'})

    def test_staff_waitlist_approval_checks_csrf_on_both_public_hosts_behind_proxy(self):
        from config.security import trusted_csrf_origins
        hosts=['pushearn.xyz','push-preview.onrender.com']
        origins=trusted_csrf_origins('https://pushearn.xyz',hosts,hosts[1])
        self.grant_staff(self.owner)
        with override_settings(ALLOWED_HOSTS=hosts,CSRF_TRUSTED_ORIGINS=origins):
            for index,host in enumerate(hosts):
                with self.subTest(host=host):
                    application=WaitlistApplication.objects.create(
                        name='Invited Tester',email=f'proxy{index}@example.test',
                        role='Developer',reason='Test the hiring flow.',accepted_testing_terms=True)
                    client=Client(enforce_csrf_checks=True)
                    client.force_login(self.owner)
                    # Public HTTPS can reach Django as HTTP after TLS termination.
                    page=client.get(reverse('moderation'),HTTP_HOST=host,HTTP_X_FORWARDED_PROTO='http')
                    self.assertEqual(page.status_code,200)
                    token=re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"',page.content.decode()).group(1)
                    url=reverse('review_waitlist',args=[application.pk])
                    headers={'HTTP_HOST':host,'HTTP_X_FORWARDED_PROTO':'http',
                             'HTTP_ORIGIN':f'https://{host}','HTTP_REFERER':f'https://{host}/moderation/'}
                    data={'decision':'approve','csrfmiddlewaretoken':token}
                    self.assertEqual(client.post(url,data,**{**headers,'HTTP_ORIGIN':'https://attacker.example'}).status_code,403)
                    self.assertEqual(client.post(url,{'decision':'approve'},**headers).status_code,403)
                    self.assertEqual(client.post(url,{**data,'csrfmiddlewaretoken':'A'*64},**headers).status_code,403)
                    application.refresh_from_db()
                    self.assertEqual(application.status,'pending')
                    self.assertFalse(application.invitations.exists())
                    response=client.post(url,data,**headers)
                    self.assertEqual(response.status_code,302)
                    self.assertEqual(response.url,reverse('staff_invitations'))
                    application.refresh_from_db()
                    self.assertEqual(application.status,'approved')
                    self.assertEqual(application.invitations.count(),1)
            self.assertEqual(len(mail.outbox),2)

    def test_login_makes_new_tester_route_prominent(self):
        response=self.client.get(reverse('login'))
        self.assertContains(response,'Create your tester account')
        self.assertContains(response,'Use invitation code')
        self.assertContains(response,'Join as a tester')
        self.assertContains(response,'class="tester-entry"')
    def test_staff_can_create_copy_and_revoke_direct_invitation(self):
        self.grant_staff(self.owner);self.login_as(self.owner)
        response=self.client.post(reverse('create_staff_invitation'),{
            'name':'Founder Friend','email':'friend@example.test','role':'Product designer',
        },follow=True)
        self.assertEqual(response.status_code,200)
        match=re.search(r'PUSH-[A-F0-9]{8}-[A-F0-9]{8}',response.content.decode())
        self.assertIsNotNone(match)
        code=match.group(0)
        invitation=Invitation.objects.get(email='friend@example.test')
        self.assertIsNone(invitation.revoked_at)
        self.assertEqual(len(mail.outbox),1);self.assertIn(code,mail.outbox[0].body)
        self.assertTrue(EmailDelivery.objects.filter(invitation=invitation,status='sent').exists())
        self.assertNotContains(self.client.get(reverse('staff_invitations')),code)
        self.client.post(reverse('revoke_invitation',args=[invitation.pk]))
        invitation.refresh_from_db();self.assertIsNotNone(invitation.revoked_at)
        self.client.logout()
        response=self.client.post(reverse('invite_redeem'),{'code':code})
        self.assertContains(response,'invalid, expired, revoked or already used')
    def test_non_staff_cannot_manage_invitations(self):
        self.login_as(self.worker)
        self.assertEqual(self.client.get(reverse('staff_invitations')).status_code,403)
        self.assertEqual(self.client.post(reverse('create_staff_invitation'),{
            'name':'No Access','email':'blocked@example.test','role':'Tester',
        }).status_code,403)
        application=WaitlistApplication.objects.create(name='Tester',email='invite@example.test',role='Tester',intended_use='Test',reason='Test',accepted_testing_terms=True)
        invitation=Invitation.objects.create(application=application,email=application.email,code_hash=hash_invitation_code('PUSH-AAAABBBB-CCCCDDDD'),created_by=self.owner,expires_at=timezone.now()+timedelta(days=7))
        self.assertEqual(self.client.post(reverse('revoke_invitation',args=[invitation.pk])).status_code,403)

    def test_trust_support_can_issue_invitation_and_open_case_desk(self):
        self.grant_staff(self.owner,'trust_support');self.login_as(self.owner)
        self.assertEqual(self.client.get(reverse('moderation')).status_code,200)
        response=self.client.post(reverse('create_staff_invitation'),{
            'name':'Support Tester','email':'support-tester@example.test','role':'QA',
        },follow=True)
        self.assertRedirects(response,reverse('staff_invitations'))
        self.assertContains(response,'Copy invitation code')
        self.assertContains(self.client.get(reverse('operations_users')),'registered accounts')

    def test_invitation_rate_limit_stays_on_styled_page(self):
        for _ in range(8):
            self.client.post(reverse('invite_redeem'),{'code':'PUSH-NOTVALID-TESTCODE'})
        response=self.client.post(reverse('invite_redeem'),{'code':'PUSH-NOTVALID-TESTCODE'})
        self.assertEqual(response.status_code,429)
        self.assertContains(response,'Create your tester account',status_code=429)
        self.assertContains(response,'Too many attempts',status_code=429)

    def test_staff_settings_and_sign_out_are_accessible(self):
        self.grant_staff(self.owner,'trust_support');self.login_as(self.owner)
        settings_page=self.client.get(reverse('account_settings'))
        self.assertContains(settings_page,'Sign out of Push')
        self.assertContains(settings_page,'Change password')
        self.assertEqual(self.client.get(reverse('password_change')).status_code,200)
        self.assertRedirects(self.client.post(reverse('logout')),reverse('home'),fetch_redirect_response=False)

    @override_settings(PUSH_BREVO_API_KEY='test-api-key')
    def test_https_email_backend_submits_verified_sender_without_smtp(self):
        class Accepted:
            status=201
            def __enter__(self): return self
            def __exit__(self,*_): return False
        captured={}
        def accept(request,timeout):
            captured['url']=request.full_url
            captured['payload']=json.loads(request.data)
            captured['timeout']=timeout
            return Accepted()
        with patch('core.email_backend.urlopen',side_effect=accept):
            count=BrevoEmailBackend().send_messages([EmailMessage('Verify','Code','Push <sender@example.test>',['tester@example.test'])])
        self.assertEqual(count,1)
        self.assertEqual(captured['url'],'https://api.brevo.com/v3/smtp/email')
        self.assertEqual(captured['payload']['sender']['email'],'sender@example.test')
        self.assertEqual(captured['payload']['to'],[{'email':'tester@example.test'}])
    def test_staff_portal_uses_approved_role_and_separate_login(self):
        self.assertRedirects(self.client.get(reverse('moderation')),f'{reverse("staff_login")}?next={reverse("moderation")}')
        self.login_as(self.worker)
        self.assertContains(self.client.get(reverse('moderation')),'Approved staff only',status_code=403)
        self.client.logout()
        denied=self.client.post(reverse('staff_login'),{'username':self.worker.email,'password':'Independent-cobalt-732!'})
        self.assertContains(denied,'has not been approved',status_code=200)
        self.grant_staff(self.owner,'admin')
        approved=self.client.post(reverse('staff_login'),{'username':self.owner.email,'password':'Independent-cobalt-732!'})
        self.assertRedirects(approved,reverse('staff_entry'),fetch_redirect_response=False)
        entry=self.client.get(reverse('staff_entry'))
        self.assertRedirects(entry,reverse('staff_dashboard'),fetch_redirect_response=False)
        self.assertContains(self.client.get(reverse('staff_team')),'Operations team')

    def test_google_staff_login_points_to_staff_entry(self):
        if not settings.GOOGLE_AUTH_ENABLED:
            self.skipTest('Google authentication is not configured in this environment.')
        response=self.client.get(reverse('staff_login'))
        self.assertContains(response,'Choose a Google account')
        self.assertContains(response,'staff%2Fentry',html=False)

    @override_settings(ACCOUNT_DEFAULT_HTTP_PROTOCOL='https')
    def test_google_oauth_uses_https_callback_behind_render(self):
        if not settings.GOOGLE_AUTH_ENABLED:
            self.skipTest('Google authentication is not configured in this environment.')
        response=self.client.get(reverse('google_login'))
        self.assertEqual(response.status_code,302)
        self.assertIn(
            'redirect_uri=https%3A%2F%2Ftestserver%2Faccounts%2Fgoogle%2Flogin%2Fcallback%2F',
            response['Location'],
        )
    def test_analytics_is_private_and_uses_existing_records(self):
        self.assertRedirects(self.client.get(reverse('analytics')),f'{reverse("login")}?next={reverse("analytics")}')
        self.login_as(self.worker)
        response=self.client.get(reverse('analytics'))
        self.assertContains(response,'Work performance')
        self.assertContains(response,'No private data is sent to an external AI')
    def test_support_ticket_moves_between_member_and_staff(self):
        self.login_as(self.worker)
        response=self.client.post(reverse('support'),{
            'subject':'Wallet balance question','category':'payment','description':'My public testnet balance needs review.',
        })
        ticket=SupportTicket.objects.get(requester=self.worker)
        self.assertRedirects(response,reverse('support_ticket',args=[ticket.pk]))
        self.client.logout();self.grant_staff(self.owner,'trust_support')
        self.login_as(self.owner)
        response=self.client.post(reverse('operations_ticket',args=[ticket.pk]),{
            'reply-body':'We are checking the public address and network.','send_reply':'1',
        })
        self.assertRedirects(response,reverse('operations_ticket',args=[ticket.pk]))
        ticket.refresh_from_db();self.assertEqual(ticket.status,'waiting_user');self.assertEqual(ticket.assigned_to,self.owner)
        self.assertTrue(Notification.objects.filter(recipient=self.worker,kind='support').exists())
        self.assertTrue(AuditEvent.objects.filter(action='support.staff_reply.created').exists())
    def test_operations_panels_are_role_protected(self):
        self.login_as(self.worker)
        for name in ['operations_tickets','operations_users','operations_email','operations_payments','operations_docs']:
            with self.subTest(name=name): self.assertEqual(self.client.get(reverse(name)).status_code,403)
        self.client.logout();self.grant_staff(self.owner,'admin');self.login_as(self.owner)
        for name in ['operations_tickets','operations_users','operations_email','operations_payments','operations_docs']:
            with self.subTest(name=name): self.assertEqual(self.client.get(reverse(name)).status_code,200)

    def test_staff_roles_only_open_their_assigned_queues(self):
        self.grant_staff(self.owner,'trust_support');self.login_as(self.owner)
        self.assertEqual(self.client.get(reverse('operations_tickets')).status_code,200)
        self.assertEqual(self.client.get(reverse('operations_users')).status_code,200)
        self.assertEqual(self.client.get(reverse('operations_payments')).status_code,200)
        self.assertEqual(self.client.get(reverse('operations_email')).status_code,403)
        self.assertEqual(self.client.get(reverse('operations_docs')).status_code,403)

    def test_each_staff_role_has_a_distinct_dashboard(self):
        cases=[
            ('owner','owner_dashboard','Owner control'),
            ('admin','admin_dashboard','Administration'),
            ('trust_support','trust_support_dashboard','Trust &amp; Support'),
        ]
        for role,route,heading in cases:
            with self.subTest(role=role):
                self.client.logout();self.grant_staff(self.owner,role);self.login_as(self.owner)
                self.assertRedirects(self.client.get(reverse('staff_dashboard')),reverse(route))
                self.assertContains(self.client.get(reverse(route)),heading)
                for other_role,other_route,_ in cases:
                    if other_role != role and role != 'owner':
                        self.assertEqual(self.client.get(reverse(other_route)).status_code,403)

    def test_owner_can_view_all_dashboards_without_changing_role(self):
        self.grant_staff(self.owner,'owner');self.login_as(self.owner)
        for role in ['owner','admin','trust_support']:
            with self.subTest(role=role):
                response=self.client.get(reverse(role+'_dashboard'))
                self.assertContains(response,'Owner workspace switcher')
                self.assertEqual(response.context['staff_portal_role'],role)
                if role != 'owner':
                    self.assertContains(response,'Your account and owner permissions have not changed')
        self.assertEqual(StaffAccess.objects.get(user=self.owner).role,'owner')
        self.client.logout();self.grant_staff(self.worker,'trust_support');self.login_as(self.worker)
        self.assertNotContains(self.client.get(reverse('trust_support_dashboard')),'Owner workspace switcher')
        self.assertEqual(self.client.get(reverse('owner_dashboard')+'?role=owner').status_code,403)

    def test_workspace_return_is_only_visible_to_approved_staff(self):
        self.login_as(self.worker)
        self.assertNotContains(self.client.get(reverse('workspace')), 'Staff workspace switch')
        self.grant_staff(self.worker, 'admin')
        self.assertRedirects(self.client.get(reverse('workspace')),reverse('staff_dashboard'),fetch_redirect_response=False)
        self.assertRedirects(self.client.get(reverse('staff_entry')),reverse('staff_dashboard'),fetch_redirect_response=False)
        self.assertRedirects(self.client.get(reverse('staff_dashboard')),reverse('admin_dashboard'))
        self.assertNotContains(self.client.get(reverse('admin_dashboard')), 'Open member workspace')
        self.assertEqual(self.client.get(reverse('owner_dashboard')).status_code, 403)
        self.client.logout();self.grant_staff(self.owner,'owner');self.login_as(self.owner)
        self.assertContains(self.client.get(reverse('workspace')),'Staff workspace switch')
        self.assertContains(self.client.get(reverse('owner_dashboard')),'Open member workspace')

    def test_operations_pages_use_a_staff_specific_mobile_dock(self):
        self.grant_staff(self.owner,'admin');self.login_as(self.owner)
        response=self.client.get(reverse('admin_dashboard'))
        self.assertContains(response,'staff-mobile-dock')
        self.assertContains(response,'>Control<',html=False)
        self.assertContains(response,'>Team<',html=False)
        self.assertContains(response,'>Cases<',html=False)
        self.assertNotContains(response,'>My jobs<',html=False)

    def test_staff_insights_are_scoped_to_the_approved_role(self):
        self.login_as(self.worker)
        self.assertEqual(self.client.get(reverse('operations_analytics')).status_code,403)
        self.client.logout();self.grant_staff(self.owner,'admin');self.login_as(self.owner)
        admin=self.client.get(reverse('operations_analytics'))
        self.assertContains(admin,'Total members')
        self.assertContains(admin,'Collected platform revenue')
        self.client.logout();self.grant_staff(self.owner,'trust_support');self.login_as(self.owner)
        trust_support=self.client.get(reverse('operations_analytics'))
        self.assertContains(trust_support,'Support cases opened')
        self.assertContains(trust_support,'Open disputes')
        self.assertContains(trust_support,'Support feedback')
        self.assertNotContains(trust_support,'Collected platform revenue')
        self.assertContains(trust_support,'Total members')
        self.assertContains(self.client.get(reverse('documentation')),'staff-mobile-dock')
        self.assertRedirects(self.client.get(reverse('wallet')),reverse('staff_dashboard'),fetch_redirect_response=False)

    def test_admin_can_lift_member_restriction_with_recorded_reason(self):
        sanction=AccountSanction.objects.create(user=self.worker,kind='suspension',reason='Case review',created_by=self.owner)
        self.grant_staff(self.owner,'admin');self.login_as(self.owner)
        url=reverse('lift_sanction',args=[self.worker.pk,sanction.pk])
        self.assertEqual(self.client.post(url,{'reason':'short'}).status_code,400)
        self.assertRedirects(self.client.post(url,{'reason':'Evidence reviewed and restriction no longer applies.'}),reverse('operations_user',args=[self.worker.pk]))
        sanction.refresh_from_db()
        self.assertFalse(sanction.active)
        self.assertEqual(sanction.lifted_by,self.owner)
        self.assertTrue(AuditEvent.objects.filter(action='account.sanction.lifted',target_id=str(sanction.pk)).exists())
        self.assertEqual(self.client.post(url,{'reason':'Repeat reversal should be rejected.'}).status_code,409)
        self.client.logout();self.grant_staff(self.owner,'trust_support');self.login_as(self.owner)
        self.assertEqual(self.client.post(url,{'reason':'Unauthorised reversal.'}).status_code,403)

    def test_restricted_member_can_appeal_but_cannot_use_work_or_wallet(self):
        AccountSanction.objects.create(user=self.worker,kind='ban',reason='A disputed case needs review.',created_by=self.owner)
        self.login_as(self.worker)
        response=self.client.get(reverse('workspace'))
        self.assertContains(response,'Request a review',status_code=403)
        self.assertContains(self.client.get(reverse('support')),'Support')
        self.assertEqual(self.client.get(reverse('wallet')).status_code,403)
        ticket_response=self.client.post(reverse('support'),{
            'subject':'Appeal account restriction','category':'account',
            'description':'Please review the evidence and let me know the decision.',
        })
        self.assertEqual(ticket_response.status_code,302)
        self.assertTrue(SupportTicket.objects.filter(requester=self.worker,category='account').exists())

    def test_admin_may_approve_trust_support_but_not_another_administrator(self):
        self.grant_staff(self.owner,'admin');self.login_as(self.owner)
        denied=self.client.post(reverse('staff_team'),{'email':self.worker.email,'role':'admin'})
        self.assertContains(denied,'Only an owner can grant owner or administrator access.')
        self.assertFalse(StaffAccess.objects.filter(user=self.worker).exists())
        approved=self.client.post(reverse('staff_team'),{'email':self.worker.email,'role':'trust_support'})
        self.assertRedirects(approved,reverse('staff_team'))
        self.assertEqual(StaffAccess.objects.get(user=self.worker).role,'trust_support')

    def test_ticket_feedback_is_one_rating_from_the_requester_after_resolution(self):
        ticket=SupportTicket.objects.create(requester=self.worker,subject='Help',category='account',description='Please help',status='resolved')
        url=reverse('support_feedback',args=[ticket.pk])
        self.login_as(self.outsider)
        self.assertEqual(self.client.post(url,{'rating':'5'}).status_code,404)
        self.client.logout();self.login_as(self.worker)
        self.assertContains(self.client.get(reverse('support_ticket',args=[ticket.pk])),'Send feedback')
        self.assertRedirects(self.client.post(url,{'rating':'5','comment':'Helpful answer.'}),reverse('support_ticket',args=[ticket.pk]))
        self.assertEqual(TicketFeedback.objects.get(ticket=ticket).rating,5)
        self.assertContains(self.client.get(reverse('support_ticket',args=[ticket.pk])),'You rated this answer 5 out of 5')
        self.assertEqual(self.client.post(url,{'rating':'1'}).status_code,409)
        self.client.logout();self.grant_staff(self.owner,'trust_support');self.login_as(self.owner)
        self.assertContains(self.client.get(reverse('operations_analytics')),'1 of 1')

    @override_settings(PUSH_BOOTSTRAP_OWNER_EMAILS={'worker@example.test'})
    def test_verified_environment_owner_is_bootstrapped_once(self):
        StaffAccess.objects.filter(user=self.worker).delete()
        self.login_as(self.worker)
        response=self.client.get(reverse('staff_entry'))
        self.assertEqual(response.status_code,200)
        access=StaffAccess.objects.get(user=self.worker)
        self.assertEqual(access.role,'owner');self.assertEqual(access.status,'approved')
        access.status='revoked';access.save(update_fields=['status'])
        self.assertEqual(self.client.get(reverse('staff_entry')).status_code,403)

    def test_bootstrap_owner_requires_an_existing_verified_account(self):
        output=StringIO()
        call_command('bootstrap_owner',self.worker.email,stdout=output)
        access=StaffAccess.objects.get(user=self.worker)
        self.assertEqual(access.role,'owner');self.assertEqual(access.status,'approved')
        self.assertTrue(User.objects.get(pk=self.worker.pk).is_staff)
        self.assertIn('Owner access granted',output.getvalue())
    def test_documentation_audience_and_email_delivery_log(self):
        public=DocumentationArticle.objects.create(slug='public-test',title='Public test',summary='Summary',body='Body',audience='public',status='published')
        staff=DocumentationArticle.objects.create(slug='staff-test',title='Staff test',summary='Summary',body='Body',audience='staff',status='published')
        self.assertEqual(self.client.get(reverse('documentation_article',args=[public.slug])).status_code,200)
        self.assertEqual(self.client.get(reverse('documentation_article',args=[staff.slug])).status_code,404)
        self.grant_invitation('mail-log@example.test')
        self.client.post(reverse('register'),{
            'display_name':'Mail Log','email':'mail-log@example.test','password1':'Long-example-password-723!',
            'password2':'Long-example-password-723!','accept_terms':'on',
        })
        self.assertTrue(EmailDelivery.objects.filter(recipient='mail-log@example.test',status='sent').exists())
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
        first_verification=self.client.post(reverse('verify_registration'),{'code':code})
        self.assertRedirects(first_verification,reverse('verification_success'))
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
        old_session=c.cookies[settings.SESSION_COOKIE_NAME].value
        self.assertEqual(c.post(reverse('logout')).status_code,403)
        c.get(reverse('profile'));credential=c.cookies[settings.CSRF_COOKIE_NAME].value
        self.assertEqual(c.post(reverse('logout'),{'csrfmiddlewaretoken':credential}).status_code,302)
        attacker=Client();attacker.cookies[settings.SESSION_COOKIE_NAME]=old_session
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
        owner_view=self.client.get(reverse('job_detail',args=[self.job.pk]))
        self.assertContains(owner_view,'Private proposal example')
        self.assertContains(owner_view,'candidate-card')
        self.assertContains(owner_view,'What I will deliver')
        self.assertContains(owner_view,'Select this worker')
        self.assertContains(owner_view,'Private member profile')
        self.assertNotContains(owner_view,reverse('public_profile',args=[self.worker.pk]))
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
    @patch('core.views.prepare_payment')
    def test_general_transfers_are_rejected_for_addresses_and_emails(self, prepare):
        source=Keypair.random().public_key
        self.worker.stellar_address=source;self.worker.save(update_fields=['stellar_address'])
        self.login_as(self.worker);self.connect_wallet_session(source)
        for destination in [Keypair.random().public_key,self.owner.email]:
            response=self.client.post(reverse('wallet_prepare'),data={
                'destination':destination,'asset':'XLM','amount':'1','memo':'Test',
            },content_type='application/json')
            self.assertEqual(response.status_code,403)
        prepare.assert_not_called()
        self.assertFalse(WalletTransfer.objects.exists())

    def test_signed_payment_must_exactly_match_server_prepared_transaction(self):
        source=Keypair.random();destination=Keypair.random().public_key
        prepared=build_payment_xdr(
            source_account=Account(source.public_key,10),destination=destination,
            amount='12.5',memo='Push transfer',asset='XLM',base_fee=100,
        )
        from stellar_sdk import TransactionEnvelope
        envelope=TransactionEnvelope.from_xdr(prepared['xdr'],Network.TESTNET_NETWORK_PASSPHRASE)
        envelope.sign(source)
        validated=validate_signed_payment(
            signed_xdr=envelope.to_xdr(),source=source.public_key,destination=destination,
            amount='12.5',memo='Push transfer',asset='XLM',
            transaction_body_digest=prepared['transaction_body_digest'],
        )
        self.assertEqual(validated.hash_hex(),envelope.hash_hex())
        with self.assertRaises(StellarVerificationError):
            validate_signed_payment(
                signed_xdr=envelope.to_xdr(),source=source.public_key,destination=destination,
                amount='12.6',memo='Push transfer',asset='XLM',
                transaction_body_digest=prepared['transaction_body_digest'],
            )

    @patch('core.views.submit_signed_payment')
    def test_previously_prepared_general_transfer_cannot_be_submitted(self, submit):
        self.login_as(self.worker)
        session=self.client.session
        session['wallet_payment_intent']={'token':'old-token','assignment':''}
        session.save()
        response=self.client.post(reverse('wallet_submit'),data={
            'token':'old-token','signedXdr':'signed-xdr',
        },content_type='application/json')
        self.assertEqual(response.status_code,403)
        submit.assert_not_called()
        self.assertNotIn('wallet_payment_intent',self.client.session)

    @patch('core.views.submit_signed_payment')
    @patch('core.views.prepare_payment')
    def test_freighter_assignment_payment_completes_work_record(self, prepare, submit):
        owner_address=Keypair.random().public_key;worker_address=Keypair.random().public_key
        self.owner.stellar_address=owner_address;self.owner.save(update_fields=['stellar_address'])
        self.worker.stellar_address=worker_address;self.worker.save(update_fields=['stellar_address'])
        item=self.make_assignment('submitted');item.payment_method='stellar_usdc_testnet';item.save(update_fields=['payment_method'])
        prepare.return_value={'xdr':'unsigned-xdr','transaction_body_digest':'1'*64,'network_passphrase':Network.TESTNET_NETWORK_PASSPHRASE}
        submit.return_value='b'*64
        self.login_as(self.owner)
        self.connect_wallet_session(owner_address)
        prepared=self.client.post(reverse('wallet_prepare'),data={'assignment':str(item.pk)},content_type='application/json').json()
        response=self.client.post(reverse('wallet_submit'),data={
            'token':prepared['token'],'signedXdr':'signed-xdr',
        },content_type='application/json')
        self.assertEqual(response.status_code,200)
        item.refresh_from_db();self.assertEqual(item.status,'paid')
        payment=Payment.objects.get(assignment=item)
        self.assertFalse(payment.simulated);self.assertEqual(payment.transaction_hash,'b'*64)
        self.assertEqual(WalletTransfer.objects.get(assignment=item).destination,worker_address)

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
    def test_wallet_disconnect_ends_session_but_keeps_receiving_address(self):
        address='GBBD47IF6LWK7P7MDEVSCWR7DPUWV3NY3DTQEVFL4NAT4AQH3ZLLFLA5'
        self.worker.stellar_address=address;self.worker.save(update_fields=['stellar_address'])
        self.login_as(self.worker)
        self.connect_wallet_session(address)
        self.assertContains(self.client.get(reverse('wallet')),'Disconnect')
        self.assertEqual(self.client.get(reverse('wallet_disconnect')).status_code,405)
        response=self.client.post(reverse('wallet_disconnect'))
        self.assertRedirects(response,reverse('wallet'))
        self.worker.refresh_from_db();self.assertEqual(self.worker.stellar_address,address)
        self.assertNotIn('wallet_connected_address',self.client.session)

    def test_wallet_prepare_requires_a_live_freighter_session(self):
        address=Keypair.random().public_key
        self.worker.stellar_address=address;self.worker.save(update_fields=['stellar_address'])
        self.login_as(self.worker)
        response=self.client.post(reverse('wallet_prepare'),data={
            'destination':Keypair.random().public_key,'asset':'XLM','amount':'1','memo':'Push test',
        },content_type='application/json')
        self.assertEqual(response.status_code,400)
        self.assertIn('Reconnect Freighter',response.json()['message'])

    def test_wallet_prepare_rejects_a_stale_session_after_receiving_address_changes(self):
        old_address=Keypair.random().public_key
        self.worker.stellar_address=Keypair.random().public_key
        self.worker.save(update_fields=['stellar_address'])
        self.login_as(self.worker)
        self.connect_wallet_session(old_address)
        response=self.client.post(reverse('wallet_prepare'),data={
            'destination':Keypair.random().public_key,'asset':'XLM','amount':'1','memo':'Push test',
        },content_type='application/json')
        self.assertEqual(response.status_code,400)
        self.assertIn('Reconnect Freighter',response.json()['message'])
        self.assertNotIn('wallet_connected_address',self.client.session)

    def test_prepare_payment_identifies_an_unfunded_source_before_the_recipient(self):
        source=Keypair.random().public_key;destination=Keypair.random().public_key
        def missing_account(_address, *, missing_message):
            raise StellarVerificationError(missing_message)
        with patch('core.stellar.account_balances',side_effect=missing_account):
            with self.assertRaisesRegex(StellarVerificationError,'active Freighter account'):
                prepare_payment(source=source,destination=destination,amount='1',memo='Push test')

    def test_prepare_payment_identifies_a_missing_recipient_separately(self):
        source=Keypair.random().public_key;destination=Keypair.random().public_key
        funded={'xlm':Decimal('10'),'usdc':Decimal('0'),'has_usdc_trustline':False}
        def account_or_missing(address, *, missing_message):
            if address == source:
                return funded
            raise StellarVerificationError(missing_message)
        with patch('core.stellar.account_balances',side_effect=account_or_missing):
            with self.assertRaisesRegex(StellarVerificationError,'recipient .* does not exist'):
                prepare_payment(source=source,destination=destination,amount='1',memo='Push test')

    def test_wallet_sync_clears_stale_connection_and_detects_account_change(self):
        saved=Keypair.random().public_key;active=Keypair.random().public_key
        self.worker.stellar_address=saved;self.worker.save(update_fields=['stellar_address'])
        self.login_as(self.worker);self.connect_wallet_session(saved)
        disconnected=self.client.post(reverse('wallet_sync'),data={'connected':False},content_type='application/json')
        self.assertEqual(disconnected.status_code,200)
        self.assertFalse(disconnected.json()['connected'])
        self.assertNotIn('wallet_connected_address',self.client.session)
        changed=self.client.post(reverse('wallet_sync'),data={
            'connected':True,'address':active,'network':'TESTNET',
        },content_type='application/json')
        self.assertEqual(changed.json()['state'],'mismatch')
        self.worker.refresh_from_db();self.assertEqual(self.worker.stellar_address,saved)

    def test_wallet_sync_restores_matching_testnet_session(self):
        address=Keypair.random().public_key
        self.worker.stellar_address=address;self.worker.save(update_fields=['stellar_address'])
        self.login_as(self.worker)
        response=self.client.post(reverse('wallet_sync'),data={
            'connected':True,'address':address,'network':'TESTNET',
        },content_type='application/json')
        self.assertTrue(response.json()['connected'])
        self.assertEqual(self.client.session['wallet_connected_address'],address)

    def test_wallet_shows_recorded_and_pending_job_values_separately(self):
        paid=self.make_assignment('paid')
        Payment.objects.create(assignment=paid,amount=400,method='usdc')
        second_job=Job.objects.create(owner=self.owner,project='Pending',title='Pending work',description='Brief',deliverables='Export',category='Design',budget=250,deadline=timezone.localdate()+timedelta(days=7),moderation_status='approved',status='assigned')
        Assignment.objects.create(job=second_job,worker=self.worker,scope='Export',budget=250,status='funded')
        self.login_as(self.worker)
        response=self.client.get(reverse('wallet'))
        self.assertContains(response,'Job earnings are separate from wallet assets')
        self.assertContains(response,'$400.00')
        self.assertContains(response,'$250.00')
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
        self.assertEqual(self.client.session['wallet_connected_address'],address)

    def test_wallet_connect_uses_render_safe_csrf_meta_token(self):
        address='GBBD47IF6LWK7P7MDEVSCWR7DPUWV3NY3DTQEVFL4NAT4AQH3ZLLFLA5'
        client=Client(enforce_csrf_checks=True)
        client.force_login(self.worker)
        page=client.get(reverse('wallet'))
        match=re.search(r'<meta name="csrf-token" content="([^"]+)">',page.content.decode())
        self.assertIsNotNone(match)
        self.assertIn(settings.CSRF_COOKIE_NAME,client.cookies)
        response=client.post(
            reverse('wallet_connect'),
            data=json.dumps({'address':address,'network':'TESTNET'}),
            content_type='application/json',
            HTTP_X_CSRFTOKEN=match.group(1),
        )
        self.assertEqual(response.status_code,200)
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

    @override_settings(PRODUCTION=True,PUSH_ORIGIN='https://pushearn.xyz',SECURE_HSTS_SECONDS=31536000,
                       SECURE_HSTS_INCLUDE_SUBDOMAINS=True,SECURE_HSTS_PRELOAD=True)
    def test_render_edge_receives_hsts_policy(self):
        response=self.client.get(reverse('home'))
        self.assertEqual(response['Strict-Transport-Security'],'max-age=31536000; includeSubDomains; preload')
    def test_password_reset_single_use_and_revokes_old_session(self):
        self.login_as(self.worker)
        old_session=self.client.cookies[settings.SESSION_COOKIE_NAME].value
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
        attacker=Client();attacker.cookies[settings.SESSION_COOKIE_NAME]=old_session
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
        self.grant_staff(self.owner);self.login_as(self.owner)
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
        self.grant_staff(self.owner);self.login_as(self.owner)
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

    def test_application_and_payment_activity_send_email_after_commit(self):
        self.login_as(self.worker)
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(reverse('apply',args=[self.job.pk]),{'proposal':'A specific proposal for the brief.'})
        self.assertEqual(mail.outbox[-1].to,[self.owner.email])
        self.assertIn('New application received',mail.outbox[-1].subject)
        self.assertTrue(EmailDelivery.objects.filter(recipient=self.owner.email,category='notification_application',status='sent').exists())

        application=Application.objects.get(job=self.job,worker=self.worker)
        self.login_as(self.owner)
        self.client.post(reverse('select',args=[application.pk]))
        item=Assignment.objects.get(job=self.job)
        item.status='submitted';item.payment_method='usdc';item.save(update_fields=['status','payment_method'])
        with self.captureOnCommitCallbacks(execute=True):
            self.action(item,'approve')
        self.assertEqual(mail.outbox[-1].to,[self.worker.email])
        self.assertIn('Work approved',mail.outbox[-1].subject)
        self.assertTrue(EmailDelivery.objects.filter(recipient=self.worker.email,category='notification_approve',status='sent').exists())

    def test_work_page_separates_worker_and_hiring_views(self):
        item=self.make_assignment('funded');self.login_as(self.worker)
        response=self.client.get(reverse('work'))
        self.assertContains(response,'Jobs I’m doing')
        self.assertContains(response,item.job.title)
        self.assertNotContains(response,'Workers you selected, with the agreement')
        self.login_as(self.owner)
        response=self.client.get(reverse('work'),{'view':'hiring'})
        self.assertContains(response,'People I hired')
        self.assertContains(response,item.worker.display_name)
        self.assertNotContains(response,'Only jobs awarded to you appear here')

    def test_work_page_tabs_keep_applications_and_posted_jobs_separate(self):
        Application.objects.create(job=self.job,worker=self.worker,proposal='A clear private proposal')
        self.login_as(self.worker)
        applications=self.client.get(reverse('work'),{'view':'applications'})
        self.assertContains(applications,'My applications')
        self.assertContains(applications,self.job.title)
        self.assertNotContains(applications,'Your published briefs and the applications')
        self.login_as(self.owner)
        posted=self.client.get(reverse('work'),{'view':'posted'})
        self.assertContains(posted,'Jobs I posted')
        self.assertContains(posted,'1 application')
        self.assertNotContains(posted,'These are proposals you sent')

    def test_assigned_work_page_highlights_worker_actions(self):
        waiting=self.make_assignment('awaiting_acceptance')
        second_job=Job.objects.create(owner=self.owner,project='Second project',title='Deliver the final export',description='Brief',deliverables='Export',category='Video Editing',budget=250,deadline=timezone.localdate()+timedelta(days=7),moderation_status='approved')
        ready=Assignment.objects.create(job=second_job,worker=self.worker,scope='Export',budget=250,status='funded')
        self.login_as(self.worker)
        legacy=self.client.get(reverse('assigned_work'))
        self.assertRedirects(legacy,reverse('work')+'?view=assigned')
        response=self.client.get(legacy.url)
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

    def test_launch_hardening_settings_match_upload_and_cookie_contract(self):
        self.assertGreaterEqual(settings.DATA_UPLOAD_MAX_MEMORY_SIZE,7*1024*1024)
        self.assertGreaterEqual(settings.FILE_UPLOAD_MAX_MEMORY_SIZE,5*1024*1024)
        self.assertEqual(settings.DATA_UPLOAD_MAX_NUMBER_FIELDS,100)

    def test_security_headers_and_rate_limit_retry_are_visible(self):
        response=self.client.get(reverse('home'),HTTP_X_REQUEST_ID='valid-request-123')
        self.assertEqual(response['X-Request-ID'],'valid-request-123')
        self.assertEqual(response['Cross-Origin-Opener-Policy'],'same-origin')
        self.assertEqual(response['Cross-Origin-Resource-Policy'],'same-origin')
        with patch('core.views.limited',return_value=True):
            limited_response=self.client.post(reverse('login'),{})
        self.assertEqual(limited_response.status_code,429)
        self.assertEqual(limited_response['Retry-After'],'900')

    def test_only_verified_accounts_can_receive_staff_access(self):
        unverified=User.objects.create_user(username='pending@example.test',email='pending@example.test',password='Independent-cobalt-732!',display_name='Pending')
        self.grant_staff(self.owner,'owner');self.login_as(self.owner)
        response=self.client.post(reverse('staff_team'),{'email':unverified.email,'role':'trust_support'})
        self.assertEqual(response.status_code,200)
        self.assertContains(response,'Create and verify this member account')
        self.assertFalse(StaffAccess.objects.filter(user=unverified).exists())

    def test_support_guidance_stays_inside_operations(self):
        DocumentationArticle.objects.create(slug='support-process',title='Support process',summary='Handle member cases.',body='Procedure',audience='staff',status='published')
        self.grant_staff(self.worker,'trust_support');self.login_as(self.worker)
        response=self.client.get(reverse('staff_guide'))
        self.assertEqual(response.status_code,200)
        self.assertContains(response,'Support process')
        self.assertContains(response,'Support operations')
        self.assertEqual(self.client.get(reverse('operations_docs')).status_code,403)

    def test_account_deletion_request_is_a_single_audited_ticket(self):
        self.login_as(self.worker)
        first=self.client.post(reverse('request_account_deletion'))
        ticket=SupportTicket.objects.get(requester=self.worker,subject='Account deletion request')
        self.assertRedirects(first,reverse('support_ticket',args=[ticket.pk]))
        second=self.client.post(reverse('request_account_deletion'))
        self.assertRedirects(second,reverse('support_ticket',args=[ticket.pk]))
        self.assertEqual(SupportTicket.objects.filter(requester=self.worker,subject='Account deletion request').count(),1)
        self.assertTrue(AuditEvent.objects.filter(action='privacy.deletion_requested',target_id=str(ticket.pk)).exists())

    def test_public_legal_pages_cover_cookies_and_refunds(self):
        cookie_policy=self.client.get(reverse('cookies'))
        self.assertContains(cookie_policy,'Necessary cookies')
        self.assertContains(cookie_policy,'Optional cookies')
        home=self.client.get(reverse('home'))
        self.assertContains(home,'Accept optional cookies')
        self.assertContains(home,'Decline optional cookies')
        self.assertContains(self.client.get(reverse('refunds')),'does not charge platform fees')

    def test_privileged_writes_are_rate_limited(self):
        self.grant_staff(self.owner,'owner');self.login_as(self.owner)
        with patch('core.access._staff_write_limited',return_value=True):
            response=self.client.post(reverse('staff_team'),{})
        self.assertEqual(response.status_code,429)
        self.assertEqual(response['Retry-After'],'900')

    @override_settings(PUSH_EMAIL_DAILY_LIMIT=1)
    def test_email_spend_guard_blocks_excess_recipients(self):
        from .mailer import EmailDailyLimitError, send_tracked_email
        send_tracked_email(category='verification',subject='One',message='Hello',recipients=['one@example.test'])
        with self.assertRaises(EmailDailyLimitError):
            send_tracked_email(category='verification',subject='Two',message='Hello',recipients=['two@example.test'])

    def test_public_seo_discovery_files_are_available(self):
        robots=self.client.get(reverse('robots'))
        self.assertEqual(robots.status_code,200)
        self.assertEqual(robots['Content-Type'],'text/plain; charset=utf-8')
        self.assertContains(robots,'Sitemap: http://127.0.0.1:8765/sitemap.xml')
        self.assertContains(robots,'Disallow: /staff/')
        sitemap=self.client.get(reverse('sitemap'))
        self.assertEqual(sitemap.status_code,200)
        self.assertEqual(sitemap['Content-Type'],'application/xml; charset=utf-8')
        self.assertContains(sitemap,'<loc>http://127.0.0.1:8765/</loc>')
        self.assertContains(sitemap,'<loc>http://127.0.0.1:8765/about/</loc>')
        self.assertContains(sitemap,'<loc>http://127.0.0.1:8765/privacy/</loc>')
        security=self.client.get(reverse('security_contact'))
        self.assertContains(security,'Expires: 2027-10-01T23:59:59Z')
        self.assertContains(security,'Canonical: http://127.0.0.1:8765/.well-known/security.txt')

    def test_public_pages_publish_canonical_social_metadata(self):
        home=self.client.get(reverse('home'))
        self.assertContains(home,'<meta name="robots" content="index, follow, max-image-preview:large, max-snippet:-1">',html=True)
        self.assertContains(home,'<link rel="canonical" href="http://127.0.0.1:8765/">',html=True)
        self.assertContains(home,'property="og:image"')
        self.assertContains(home,'images/push-social-card-v3.png')
        self.assertContains(home,'name="twitter:site" content="@pushearn_"')
        self.assertContains(home,'"@type":"WebSite"')
        self.assertContains(home,'"@type":"WebApplication"')
        about=self.client.get(reverse('about'))
        self.assertContains(about,'not a paid-task scheme')
        self.assertContains(about,'<meta name="robots" content="index, follow, max-image-preview:large, max-snippet:-1">',html=True)
        login=self.client.get(reverse('login'))
        self.assertContains(login,'<meta name="robots" content="noindex, nofollow, noarchive">',html=True)
        self.assertNotContains(login,'rel="canonical"')

    def test_signed_in_home_redirects_to_workspace(self):
        self.login_as(self.worker)
        self.assertRedirects(self.client.get(reverse('home')),reverse('workspace'),fetch_redirect_response=False)

    def test_disconnect_survives_sync_until_explicit_reconnect(self):
        address=Keypair.random().public_key
        self.worker.stellar_address=address;self.worker.save(update_fields=['stellar_address'])
        self.login_as(self.worker);self.connect_wallet_session(address)
        self.client.post(reverse('wallet_disconnect'))
        payload={'connected':True,'address':address,'network':'TESTNET'}
        for _ in range(2):
            response=self.client.post(reverse('wallet_sync'),data=payload,content_type='application/json')
            self.assertFalse(response.json()['connected'])
            self.assertNotIn('wallet_connected_address',self.client.session)
        response=self.client.post(reverse('wallet_connect'),data=payload,content_type='application/json')
        self.assertEqual(response.status_code,200)
        self.assertNotIn('wallet_explicitly_disconnected',self.client.session)
        response=self.client.post(reverse('wallet_sync'),data=payload,content_type='application/json')
        self.assertTrue(response.json()['connected'])

    def test_message_policy_applies_to_both_endpoints_and_preserves_evidence(self):
        item=self.make_assignment()
        self.login_as(self.worker)
        routes=[reverse('assignment_message',args=[item.pk]),reverse('conversation',args=[item.pk])]
        for state,allowed in [('awaiting_acceptance',False),('awaiting_funding',True),('funded',True),('submitted',True),('disputed',True),('paid',False),('cancelled',False)]:
            item.status=state;item.save(update_fields=['status'])
            for url in routes:
                before=item.messages.count()
                response=self.client.post(url,{'body':'Preserved project evidence'})
                self.assertEqual(response.status_code,302 if allowed else 403,(state,url))
                self.assertEqual(item.messages.count(),before+(1 if allowed else 0))
        self.assertContains(self.client.get(routes[1]),'Preserved project evidence')
        self.assertContains(self.client.get(routes[1]),'read-only')
        self.assertNotContains(self.client.get(routes[1]),'class="chat-composer"')

    @patch('core.views.account_balances')
    def test_wallet_has_assignment_payments_but_no_general_send_form(self, balances):
        balances.return_value={'xlm':Decimal('10'),'usdc':Decimal('0'),'has_usdc_trustline':False}
        self.login_as(self.worker)
        response=self.client.get(reverse('wallet'))
        self.assertContains(response,'Pay through your workroom')
        self.assertNotContains(response,'data-stellar-payment')

    def test_messages_navigation_opens_after_agreement_acceptance(self):
        item=self.make_assignment();self.login_as(self.worker)
        self.assertNotContains(self.client.get(reverse('workspace')),'<span>Messages</span>')
        item.status='awaiting_funding';item.save(update_fields=['status'])
        self.assertContains(self.client.get(reverse('workspace')),'<span>Messages</span>')

    @override_settings(PUSH_DEPLOYMENT_TIER='staging')
    def test_staging_public_pages_are_identified_and_not_indexable(self):
        response=self.client.get(reverse('home'))
        self.assertContains(response,'Staging environment')
        self.assertContains(response,'noindex, nofollow, noarchive')
        self.assertEqual(self.client.get(reverse('robots')).content,b'User-agent: *\nDisallow: /\n')
        self.assertEqual(self.client.get(reverse('sitemap')).status_code,404)
