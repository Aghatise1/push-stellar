import hashlib
from datetime import datetime, timedelta, timezone as dt_timezone
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from stellar_sdk import Keypair

from core.models import Assignment, EscrowAgreement, EscrowTransaction, Job, StaffAccess, User
from core.pilot_reliability import (
    abbreviate_address,
    build_pilot_reliability_report,
    expected_chain_states,
    stale_minutes,
)


class PilotReliabilityHelperTests(SimpleTestCase):
    def test_stale_minutes_defaults_and_rejects_invalid_values(self):
        self.assertEqual(stale_minutes(), 15)
        for invalid in (None, '', 'abc', 0, -5, '0', '-10', [], {}, True, False):
            with self.subTest(invalid=invalid):
                with override_settings(PUSH_PILOT_STALE_MINUTES=invalid):
                    self.assertEqual(stale_minutes(), 15)
        for valid, expected in ((5, 5), ('20', 20), (1, 1)):
            with self.subTest(valid=valid):
                with override_settings(PUSH_PILOT_STALE_MINUTES=valid):
                    self.assertEqual(stale_minutes(), expected)

    def test_abbreviate_address_never_returns_the_full_value(self):
        self.assertEqual(abbreviate_address(''), '')
        self.assertEqual(abbreviate_address('   '), '')
        self.assertEqual(abbreviate_address(None), '')
        full_address = 'GBBD47IF6LWK7P7MDEVSCWR7DPUWV3NY3DTQEVFL4NAT4AQH3ZLLFLA5'
        short = abbreviate_address(full_address)
        self.assertTrue(short)
        self.assertNotEqual(short, full_address)
        self.assertNotIn(full_address, short)
        self.assertTrue(short.startswith('GBBD47'))
        self.assertTrue(short.endswith('FLA5'))
        short_input = 'GSHORT1234'
        abbreviated_short = abbreviate_address(short_input)
        self.assertNotEqual(abbreviated_short, short_input)

    def test_expected_chain_states_matches_spec_rules(self):
        self.assertEqual(expected_chain_states('awaiting_acceptance'), {'Unfunded'})
        self.assertEqual(expected_chain_states('awaiting_funding'), {'Unfunded'})
        self.assertEqual(expected_chain_states('funded'), {'Funded'})
        self.assertEqual(expected_chain_states('submitted'), {'Submitted'})
        self.assertEqual(expected_chain_states('disputed'), {'Disputed'})
        self.assertEqual(expected_chain_states('paid'), {'Released', 'Resolved'})
        self.assertEqual(expected_chain_states('cancelled'), {'Refunded', 'Unfunded'})
        self.assertEqual(expected_chain_states('unknown_status'), set())


class PilotReliabilityReportTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.fixed_now = datetime(2026, 10, 25, 12, 0, 0, tzinfo=dt_timezone.utc)
        accepted = cls.fixed_now - timedelta(days=2)
        cls.client_address = Keypair.random().public_key
        cls.worker_address = Keypair.random().public_key
        cls.reviewer_address = Keypair.random().public_key
        cls.owner_user = User.objects.create_user(
            username='owner@example.test',
            email='owner@example.test',
            password='Independent-cobalt-732!',
            display_name='Owner User',
            email_verified=True,
            stellar_address=cls.reviewer_address,
            terms_version='2026-10-06.1',
            terms_accepted_at=accepted,
        )
        StaffAccess.objects.create(user=cls.owner_user, role='owner', status='approved', approved_at=accepted)
        cls.client_user = User.objects.create_user(
            username='client@example.test',
            email='client@example.test',
            password='Independent-cobalt-732!',
            display_name='Client User',
            email_verified=True,
            stellar_address=cls.client_address,
            terms_version='2026-10-06.1',
            terms_accepted_at=accepted,
        )
        cls.worker_user = User.objects.create_user(
            username='worker@example.test',
            email='worker@example.test',
            password='Independent-cobalt-732!',
            display_name='Worker User',
            email_verified=True,
            stellar_address=cls.worker_address,
            terms_version='2026-10-06.1',
            terms_accepted_at=accepted,
        )
        cls.counter = 0

    def make_agreement(self, assignment_status, chain_status, *, amount=125, asset='USDC', accepted_delta_seconds=3600):
        type(self).counter += 1
        idx = type(self).counter
        job = Job.objects.create(
            owner=self.client_user,
            project=f'Project {idx}',
            title=f'Job {idx}',
            description='Private job description',
            deliverables='Deliverable spec',
            category='Development',
            budget=amount,
            payment_asset=asset,
            deadline=self.fixed_now.date() + timedelta(days=7),
            moderation_status='approved',
            status='assigned',
        )
        assignment = Assignment.objects.create(
            job=job,
            worker=self.worker_user,
            scope='Private scope details',
            budget=amount,
            status=assignment_status,
            escrow_required=True,
            accepted_terms_at=self.fixed_now - timedelta(seconds=accepted_delta_seconds),
        )
        agreement = EscrowAgreement.objects.create(
            staff_governed=True,
            assignment=assignment,
            reviewer=self.owner_user,
            contract='CCONTRACT1234567890123456789012345678901234567890123456',
            agreement_id=hashlib.sha256(f'agreement-{idx}'.encode()).hexdigest(),
            client_address=self.client_address,
            worker_address=self.worker_address,
            reviewer_address=self.reviewer_address,
            asset=asset,
            token_address='CTOKEN1234567890123456789012345678901234567890123456789',
            amount=amount,
            deadline=int((self.fixed_now + timedelta(days=7)).timestamp()),
            review_seconds=86400,
            revision_limit=2,
            chain_status=chain_status,
            accepted_at=self.fixed_now - timedelta(seconds=accepted_delta_seconds),
        )
        return agreement

    def make_tx(self, agreement, *, action='fund', state='prepared', age_seconds=60, source=None):
        type(self).counter += 1
        idx = type(self).counter
        tx = EscrowTransaction.objects.create(
            escrow=agreement,
            actor=self.client_user,
            action=action,
            source=source or self.client_address,
            prepared_xdr=f'SECRET_PREPARED_XDR_{idx}',
            signed_xdr=f'SECRET_SIGNED_XDR_{idx}',
            tx_hash=hashlib.sha256(f'tx-{idx}'.encode()).hexdigest(),
            state=state,
        )
        created_at = self.fixed_now - timedelta(seconds=age_seconds)
        EscrowTransaction.objects.filter(pk=tx.pk).update(created_at=created_at)
        tx.refresh_from_db()
        return tx

    def test_report_aggregates_all_defined_pairs_mismatches_thresholds_and_bounds(self):
        # All 8 valid defined pairs (including agreement with no transactions)
        a_unfunded = self.make_agreement('awaiting_funding', 'Unfunded', amount=50, asset='XLM')
        a_funded = self.make_agreement('funded', 'Funded', amount=100, asset='USDC')
        a_submitted = self.make_agreement('submitted', 'Submitted', amount=150, asset='USDC')
        a_disputed = self.make_agreement('disputed', 'Disputed', amount=200, asset='XLM')
        a_paid_released = self.make_agreement('paid', 'Released', amount=250, asset='USDC')
        a_paid_resolved = self.make_agreement('paid', 'Resolved', amount=300, asset='USDC')
        a_cancelled_refunded = self.make_agreement('cancelled', 'Refunded', amount=350, asset='XLM')
        a_cancelled_unfunded = self.make_agreement('cancelled', 'Unfunded', amount=400, asset='XLM')  # no transactions

        # High-confidence mismatch
        a_mismatch = self.make_agreement('funded', 'Unfunded', amount=500, asset='USDC', accepted_delta_seconds=1200)
        # Unknown state combination
        a_unknown = self.make_agreement('unexpected_local', 'UnexpectedChain', amount=600, asset='XLM', accepted_delta_seconds=1800)

        # Transactions covering threshold and terminal states
        self.make_tx(a_unfunded, action='fund', state='prepared', age_seconds=14 * 60 + 59)  # younger than 15m -> ok
        tx_at_threshold = self.make_tx(a_funded, action='fund', state='prepared', age_seconds=15 * 60)  # exactly 15m -> attention
        tx_old_pending = self.make_tx(a_submitted, action='submit', state='pending', age_seconds=20 * 60)  # older pending -> attention
        tx_failed = self.make_tx(a_disputed, action='open_dispute', state='failed', age_seconds=120)  # failed -> attention
        self.make_tx(a_paid_released, action='approve', state='confirmed', age_seconds=3600)  # confirmed -> ok
        self.make_tx(a_paid_resolved, action='resolve', state='expired', age_seconds=7200)  # expired -> counted, not attention

        report = build_pilot_reliability_report(now=self.fixed_now)
        self.assertEqual(report['generated_at'], self.fixed_now)
        self.assertEqual(report['stale_minutes'], 15)
        self.assertIn('tier', report['deployment'])
        self.assertIn('escrow_enabled', report['deployment'])

        # Agreement counts include the transaction-less agreement and all 10 agreements
        self.assertEqual(report['agreement_counts']['total'], 10)
        self.assertEqual(report['agreement_counts']['by_assignment_status']['paid'], 2)
        self.assertEqual(report['agreement_counts']['by_assignment_status']['cancelled'], 2)
        self.assertEqual(report['agreement_counts']['by_assignment_status']['funded'], 2)
        self.assertEqual(report['agreement_counts']['by_chain_status']['Unfunded'], 3)

        # Transaction counts
        self.assertEqual(
            report['transaction_counts'],
            {
                'total': 6,
                'prepared': 2,
                'pending': 1,
                'confirmed': 1,
                'failed': 1,
                'expired': 1,
            },
        )

        # Attention items: 1 mismatch + 1 unknown + 1 at threshold + 1 older pending + 1 failed = 5
        self.assertEqual(report['attention_total'], 5)
        self.assertEqual(len(report['attention']), 5)

        allowed_keys = {'assignment_id', 'action', 'state', 'age_seconds', 'asset', 'amount', 'source', 'workroom_url'}
        serialized = str(report)
        self.assertNotIn('SECRET_PREPARED_XDR', serialized)
        self.assertNotIn('SECRET_SIGNED_XDR', serialized)
        self.assertNotIn(self.client_address, serialized)
        self.assertNotIn(self.worker_address, serialized)
        self.assertNotIn(self.reviewer_address, serialized)
        self.assertNotIn('Private scope details', serialized)
        self.assertNotIn('Private job description', serialized)

        for item in report['attention']:
            self.assertEqual(set(item.keys()), allowed_keys)
            self.assertEqual(item['workroom_url'], reverse('pilot_reliability_inspect', args=[item['assignment_id']]))
            self.assertEqual(item['source'], abbreviate_address(self.client_address))

        attention_by_assignment = {(item['assignment_id'], item['action']): item for item in report['attention']}
        self.assertIn((str(a_mismatch.assignment_id), 'state_mismatch'), attention_by_assignment)
        self.assertIn((str(a_unknown.assignment_id), 'unknown_state'), attention_by_assignment)
        self.assertEqual(
            attention_by_assignment[(str(tx_at_threshold.escrow.assignment_id), 'fund')]['age_seconds'],
            900,
        )
        self.assertEqual(
            attention_by_assignment[(str(tx_old_pending.escrow.assignment_id), 'submit')]['age_seconds'],
            1200,
        )
        self.assertEqual(
            attention_by_assignment[(str(tx_failed.escrow.assignment_id), 'open_dispute')]['state'],
            'failed',
        )

        # Bounded attention list preserves attention_total and complete counts
        bounded = build_pilot_reliability_report(now=self.fixed_now, attention_limit=2)
        self.assertEqual(bounded['attention_total'], 5)
        self.assertEqual(len(bounded['attention']), 2)
        self.assertEqual(bounded['agreement_counts']['total'], 10)
        self.assertEqual(bounded['transaction_counts']['total'], 6)

    def test_awaiting_acceptance_with_unfunded_is_valid_and_produces_no_alert(self):
        agreement = self.make_agreement('awaiting_acceptance', 'Unfunded', amount=75, asset='USDC')
        report = build_pilot_reliability_report(now=self.fixed_now)
        self.assertEqual(report['agreement_counts']['total'], 1)
        self.assertEqual(report['agreement_counts']['by_assignment_status']['awaiting_acceptance'], 1)
        self.assertEqual(report['agreement_counts']['by_chain_status']['Unfunded'], 1)
        self.assertEqual(report['agreement_counts']['by_pair'].get('awaiting_acceptance:Unfunded'), 1)
        self.assertEqual(report['attention_total'], 0)
        self.assertEqual(report['attention'], [])
        self.assertNotIn(str(agreement.assignment_id), str(report['attention']))

    def test_attention_queue_fetches_only_bounded_records_while_preserving_complete_total(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        valid_agreement = self.make_agreement('awaiting_funding', 'Unfunded', amount=50, asset='XLM')
        m1 = self.make_agreement('funded', 'Unfunded', amount=110, asset='USDC', accepted_delta_seconds=3000)
        m2 = self.make_agreement('submitted', 'Funded', amount=120, asset='XLM', accepted_delta_seconds=2400)
        m3 = self.make_agreement('paid', 'Submitted', amount=130, asset='USDC', accepted_delta_seconds=1800)

        t1 = self.make_tx(valid_agreement, action='fund', state='prepared', age_seconds=40 * 60)
        t2 = self.make_tx(m1, action='fund', state='pending', age_seconds=35 * 60)
        t3 = self.make_tx(m2, action='submit', state='failed', age_seconds=30 * 60)
        t4 = self.make_tx(m3, action='approve', state='failed', age_seconds=25 * 60)

        with CaptureQueriesContext(connection) as zero_queries:
            zero_report = build_pilot_reliability_report(now=self.fixed_now, attention_limit=0)
        self.assertEqual(zero_report['attention_total'], 7)
        self.assertEqual(zero_report['attention'], [])
        self.assertEqual(len(zero_queries), 3)

        with CaptureQueriesContext(connection) as agreement_only_queries:
            only_agreements = build_pilot_reliability_report(now=self.fixed_now, attention_limit=2)
        self.assertEqual(only_agreements['attention_total'], 7)
        self.assertEqual(len(only_agreements['attention']), 2)
        self.assertEqual(
            [(item['assignment_id'], item['action']) for item in only_agreements['attention']],
            [
                (str(m1.assignment_id), 'state_mismatch'),
                (str(m2.assignment_id), 'state_mismatch'),
            ],
        )
        self.assertEqual(len(agreement_only_queries), 4)
        self.assertIn('LIMIT 2', agreement_only_queries[-1]['sql'].upper())

        with CaptureQueriesContext(connection) as shared_queries:
            shared_report = build_pilot_reliability_report(now=self.fixed_now, attention_limit=5)
        self.assertEqual(shared_report['attention_total'], 7)
        self.assertEqual(len(shared_report['attention']), 5)
        self.assertEqual(
            [(item['assignment_id'], item['action']) for item in shared_report['attention']],
            [
                (str(m1.assignment_id), 'state_mismatch'),
                (str(m2.assignment_id), 'state_mismatch'),
                (str(m3.assignment_id), 'state_mismatch'),
                (str(t1.escrow.assignment_id), 'fund'),
                (str(t2.escrow.assignment_id), 'fund'),
            ],
        )
        self.assertEqual(len(shared_queries), 5)
        self.assertIn('LIMIT 5', shared_queries[-2]['sql'].upper())
        self.assertIn('LIMIT 2', shared_queries[-1]['sql'].upper())


class PilotReliabilityPageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.fixed_now = datetime(2026, 10, 25, 12, 0, 0, tzinfo=dt_timezone.utc)
        accepted = cls.fixed_now - timedelta(days=2)
        cls.client_address = Keypair.random().public_key
        cls.worker_address = Keypair.random().public_key
        cls.reviewer_address = Keypair.random().public_key

        cls.owner_user = User.objects.create_user(
            username='rel-owner@example.test',
            email='rel-owner@example.test',
            password='Independent-cobalt-732!',
            display_name='Rel Owner',
            email_verified=True,
            stellar_address=cls.reviewer_address,
            terms_version='2026-10-06.1',
            terms_accepted_at=accepted,
            is_staff=True,
        )
        StaffAccess.objects.create(user=cls.owner_user, role='owner', status='approved', approved_at=accepted)

        cls.admin_user = User.objects.create_user(
            username='rel-admin@example.test',
            email='rel-admin@example.test',
            password='Independent-cobalt-732!',
            display_name='Rel Admin',
            email_verified=True,
            terms_version='2026-10-06.1',
            terms_accepted_at=accepted,
            is_staff=True,
        )
        StaffAccess.objects.create(user=cls.admin_user, role='admin', status='approved', approved_at=accepted)

        cls.support_user = User.objects.create_user(
            username='rel-support@example.test',
            email='rel-support@example.test',
            password='Independent-cobalt-732!',
            display_name='Rel Support',
            email_verified=True,
            terms_version='2026-10-06.1',
            terms_accepted_at=accepted,
            is_staff=True,
        )
        StaffAccess.objects.create(user=cls.support_user, role='trust_support', status='approved', approved_at=accepted)

        cls.customer_user = User.objects.create_user(
            username='rel-customer@example.test',
            email='rel-customer@example.test',
            password='Independent-cobalt-732!',
            display_name='Rel Customer',
            email_verified=True,
            stellar_address=cls.client_address,
            terms_version='2026-10-06.1',
            terms_accepted_at=accepted,
        )

        cls.worker_user = User.objects.create_user(
            username='rel-worker@example.test',
            email='rel-worker@example.test',
            password='Independent-cobalt-732!',
            display_name='Rel Worker',
            email_verified=True,
            stellar_address=cls.worker_address,
            terms_version='2026-10-06.1',
            terms_accepted_at=accepted,
        )

        job = Job.objects.create(
            owner=cls.customer_user,
            project='Confidential Project',
            title='Confidential Job',
            description='Confidential job body',
            deliverables='Confidential deliverable',
            category='Development',
            budget=250,
            payment_asset='USDC',
            deadline=cls.fixed_now.date() + timedelta(days=7),
            moderation_status='approved',
            status='assigned',
        )
        cls.assignment = Assignment.objects.create(
            job=job,
            worker=cls.worker_user,
            scope='Confidential scope text',
            budget=250,
            status='funded',
            escrow_required=True,
            accepted_terms_at=cls.fixed_now - timedelta(hours=2),
        )
        cls.agreement = EscrowAgreement.objects.create(
            staff_governed=True,
            assignment=cls.assignment,
            reviewer=cls.owner_user,
            contract='CCONTRACT1234567890123456789012345678901234567890123456',
            agreement_id=hashlib.sha256(b'page-agreement').hexdigest(),
            client_address=cls.client_address,
            worker_address=cls.worker_address,
            reviewer_address=cls.reviewer_address,
            asset='USDC',
            token_address='CTOKEN1234567890123456789012345678901234567890123456789',
            amount=250,
            deadline=int((cls.fixed_now + timedelta(days=7)).timestamp()),
            review_seconds=86400,
            revision_limit=2,
            chain_status='Unfunded',
            accepted_at=cls.fixed_now - timedelta(hours=2),
        )
        tx = EscrowTransaction.objects.create(
            escrow=cls.agreement,
            actor=cls.customer_user,
            action='fund',
            source=cls.client_address,
            prepared_xdr='PRIVATE_PREPARED_XDR_PAYLOAD',
            signed_xdr='PRIVATE_SIGNED_XDR_PAYLOAD',
            tx_hash=hashlib.sha256(b'page-tx').hexdigest(),
            state='failed',
        )
        EscrowTransaction.objects.filter(pk=tx.pk).update(created_at=cls.fixed_now - timedelta(minutes=30))

    def test_pilot_reliability_page_enforces_owner_and_admin_access(self):
        url = reverse('pilot_reliability')
        self.assertEqual(url, '/moderation/pilot-reliability/')

        anon_response = self.client.get(url)
        self.assertEqual(anon_response.status_code, 302)
        self.assertIn(reverse('staff_login'), anon_response['Location'])

        self.client.force_login(self.customer_user)
        self.assertEqual(self.client.get(url).status_code, 403)

        self.client.force_login(self.support_user)
        self.assertEqual(self.client.get(url).status_code, 403)
        moderation_support = self.client.get(reverse('moderation'))
        self.assertEqual(moderation_support.status_code, 200)
        self.assertNotContains(moderation_support, url)

        for allowed_user in (self.owner_user, self.admin_user):
            with self.subTest(role=allowed_user.username):
                self.client.force_login(allowed_user)
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(self.client.post(url).status_code, 405)
                moderation_page = self.client.get(reverse('moderation'))
                self.assertContains(moderation_page, url)
                self.assertContains(moderation_page, 'Pilot reliability')

    def test_pilot_reliability_page_renders_safe_records_with_no_store_and_omits_sensitive_data(self):
        from core.models import Message, Submission

        Message.objects.create(assignment=self.assignment, sender=self.customer_user, body='Secret workroom message body')
        Submission.objects.create(
            assignment=self.assignment,
            author=self.worker_user,
            notes='Secret delivery evidence notes',
            link='https://example.test/secret-evidence-link',
            evidence='Confidential submission evidence details',
        )

        self.client.force_login(self.owner_user)
        response = self.client.get(reverse('pilot_reliability'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('no-store', response['Cache-Control'])
        self.assertContains(response, 'Push database records')
        self.assertContains(response, 'does not replace Stellar ledger verification')
        inspect_url = reverse('pilot_reliability_inspect', args=[self.assignment.pk])
        self.assertContains(response, inspect_url)
        self.assertNotContains(response, reverse('escrow_detail', args=[self.assignment.pk]))
        self.assertContains(response, abbreviate_address(self.client_address))

        body = response.content.decode('utf-8')
        self.assertNotIn('PRIVATE_PREPARED_XDR_PAYLOAD', body)
        self.assertNotIn('PRIVATE_SIGNED_XDR_PAYLOAD', body)
        self.assertNotIn(self.client_address, body)
        self.assertNotIn(self.worker_address, body)
        self.assertNotIn(self.reviewer_address, body)
        self.assertNotIn('rel-customer@example.test', body)
        self.assertNotIn('rel-worker@example.test', body)
        self.assertNotIn('Secret workroom message body', body)
        self.assertNotIn('Secret delivery evidence notes', body)
        self.assertNotIn('https://example.test/secret-evidence-link', body)

    def test_reliability_pages_hide_account_email_without_mutating_user(self):
        pages = (
            reverse('pilot_reliability'),
            reverse('pilot_reliability_inspect', args=[self.assignment.pk]),
        )
        for allowed_user in (self.owner_user, self.admin_user):
            original_email = allowed_user.email
            self.client.force_login(allowed_user)
            for url in pages:
                with self.subTest(user=allowed_user.username, url=url):
                    response = self.client.get(url)
                    self.assertEqual(response.status_code, 200)
                    self.assertIn('no-store', response['Cache-Control'])
                    self.assertEqual(response.wsgi_request.user.email, original_email)
                    self.assertEqual(response.context['user'].email, original_email)
                    body = response.content.decode('utf-8')
                    self.assertNotIn(original_email, body)
                    self.assertNotIn('@example.test', body)
            allowed_user.refresh_from_db()
            self.assertEqual(allowed_user.email, original_email)

    def test_ordinary_authenticated_page_still_renders_account_email(self):
        self.client.force_login(self.owner_user)
        response = self.client.get(reverse('moderation'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.owner_user.email)

    def test_pilot_reliability_inspect_page_enforces_access_without_staff_wallet_and_omits_sensitive_data(self):
        from core.models import EscrowStaffWallet, Message, Submission

        self.assertFalse(EscrowStaffWallet.objects.filter(user=self.admin_user).exists())
        Message.objects.create(assignment=self.assignment, sender=self.customer_user, body='Inspect secret message text')
        Submission.objects.create(
            assignment=self.assignment,
            author=self.worker_user,
            notes='Inspect secret delivery notes',
            link='https://example.test/inspect-secret-link',
            evidence='Inspect confidential submission evidence',
        )

        inspect_url = reverse('pilot_reliability_inspect', args=[self.assignment.pk])
        self.assertEqual(inspect_url, f'/moderation/pilot-reliability/{self.assignment.pk}/')

        # Signed-out visitors are redirected to staff login
        self.client.logout()
        anon_response = self.client.get(inspect_url)
        self.assertEqual(anon_response.status_code, 302)
        self.assertIn(reverse('staff_login'), anon_response['Location'])

        # Customers receive 403
        self.client.force_login(self.customer_user)
        self.assertEqual(self.client.get(inspect_url).status_code, 403)

        # Trust and Support receives 403
        self.client.force_login(self.support_user)
        self.assertEqual(self.client.get(inspect_url).status_code, 403)

        # Escrow workroom still requires registered staff wallet for admin (403 unchanged)
        self.client.force_login(self.admin_user)
        self.assertEqual(self.client.get(reverse('escrow_detail', args=[self.assignment.pk])).status_code, 403)

        # Owners and administrators (without registered staff wallet) can open the inspection page; POST rejected
        for allowed_user in (self.owner_user, self.admin_user):
            with self.subTest(role=allowed_user.username):
                self.client.force_login(allowed_user)
                response = self.client.get(inspect_url)
                self.assertEqual(response.status_code, 200)
                self.assertIn('no-store', response['Cache-Control'])
                self.assertEqual(self.client.post(inspect_url).status_code, 405)

                self.assertContains(response, str(self.assignment.pk))
                self.assertContains(response, 'mismatch:funded:Unfunded')
                self.assertContains(response, abbreviate_address(self.client_address))
                self.assertContains(response, abbreviate_address(self.worker_address))
                self.assertContains(response, 'Push database records')

                body = response.content.decode('utf-8')
                self.assertNotIn('PRIVATE_PREPARED_XDR_PAYLOAD', body)
                self.assertNotIn('PRIVATE_SIGNED_XDR_PAYLOAD', body)
                self.assertNotIn(self.client_address, body)
                self.assertNotIn(self.worker_address, body)
                self.assertNotIn(self.reviewer_address, body)
                self.assertNotIn('rel-customer@example.test', body)
                self.assertNotIn('rel-worker@example.test', body)
                self.assertNotIn('rel-owner@example.test', body)
                self.assertNotIn('rel-admin@example.test', body)
                self.assertNotIn('Inspect secret message text', body)
                self.assertNotIn('Inspect secret delivery notes', body)
                self.assertNotIn('https://example.test/inspect-secret-link', body)
                self.assertNotIn('Inspect confidential submission evidence', body)
                self.assertNotIn('Confidential job body', body)
                self.assertNotIn('Confidential scope text', body)


class PilotReliabilityCommandTests(TestCase):
    def setUp(self):
        accepted = timezone.now() - timedelta(days=1)
        self.client_address = Keypair.random().public_key
        self.worker_address = Keypair.random().public_key
        self.reviewer_address = Keypair.random().public_key
        self.customer = User.objects.create_user(
            username='cmd-customer@example.test',
            email='cmd-customer@example.test',
            password='Independent-cobalt-732!',
            display_name='Command Customer',
            email_verified=True,
            stellar_address=self.client_address,
            terms_version='2026-10-06.1',
            terms_accepted_at=accepted,
        )
        self.worker = User.objects.create_user(
            username='cmd-worker@example.test',
            email='cmd-worker@example.test',
            password='Independent-cobalt-732!',
            display_name='Command Worker',
            email_verified=True,
            stellar_address=self.worker_address,
            terms_version='2026-10-06.1',
            terms_accepted_at=accepted,
        )
        self.reviewer = User.objects.create_user(
            username='cmd-reviewer@example.test',
            email='cmd-reviewer@example.test',
            password='Independent-cobalt-732!',
            display_name='Command Reviewer',
            email_verified=True,
            stellar_address=self.reviewer_address,
            terms_version='2026-10-06.1',
            terms_accepted_at=accepted,
        )

    def test_check_pilot_reliability_prints_safe_summary_and_supports_fail_on_attention(self):
        from io import StringIO
        from django.core.management import call_command
        from django.core.management.base import CommandError
        from core.models import Message, Submission

        clean_out = StringIO()
        call_command('check_pilot_reliability', '--fail-on-attention', stdout=clean_out)
        self.assertIn('attention_total: 0', clean_out.getvalue())

        now = timezone.now()
        job = Job.objects.create(
            owner=self.customer,
            project='Command Reliability Project',
            title='Command Reliability Job',
            description='Private command job description',
            deliverables='Command deliverable spec',
            category='Development',
            budget=80,
            payment_asset='XLM',
            deadline=now.date() + timedelta(days=7),
            moderation_status='approved',
            status='assigned',
        )
        assignment = Assignment.objects.create(
            job=job,
            worker=self.worker,
            scope='Private command scope',
            budget=80,
            status='funded',
            escrow_required=True,
            accepted_terms_at=now - timedelta(minutes=30),
        )
        agreement = EscrowAgreement.objects.create(
            staff_governed=True,
            assignment=assignment,
            reviewer=self.reviewer,
            contract='CCONTRACT1234567890123456789012345678901234567890123456',
            agreement_id=hashlib.sha256(b'cmd-agreement').hexdigest(),
            client_address=self.client_address,
            worker_address=self.worker_address,
            reviewer_address=self.reviewer_address,
            asset='XLM',
            token_address='CTOKEN1234567890123456789012345678901234567890123456789',
            amount=80,
            deadline=int((now + timedelta(days=7)).timestamp()),
            review_seconds=86400,
            revision_limit=2,
            chain_status='Unfunded',
            accepted_at=now - timedelta(minutes=30),
        )
        tx = EscrowTransaction.objects.create(
            escrow=agreement,
            actor=self.customer,
            action='fund',
            source=self.client_address,
            prepared_xdr='CMD_SECRET_PREPARED_XDR',
            signed_xdr='CMD_SECRET_SIGNED_XDR',
            tx_hash=hashlib.sha256(b'cmd-tx').hexdigest(),
            state='failed',
        )
        EscrowTransaction.objects.filter(pk=tx.pk).update(created_at=now - timedelta(minutes=30))
        Message.objects.create(assignment=assignment, sender=self.customer, body='Private command test message')
        Submission.objects.create(
            assignment=assignment,
            author=self.worker,
            notes='Private command submission notes',
            link='https://example.test/private-cmd-evidence',
            evidence='Private command evidence text',
        )

        out = StringIO()
        call_command('check_pilot_reliability', stdout=out)
        output = out.getvalue()
        self.assertIn('Push database records', output)
        self.assertIn(str(assignment.pk), output)
        self.assertIn('state_mismatch', output)
        self.assertIn('mismatch:funded:Unfunded', output)
        self.assertIn(abbreviate_address(self.client_address), output)
        self.assertNotIn('CMD_SECRET_PREPARED_XDR', output)
        self.assertNotIn('CMD_SECRET_SIGNED_XDR', output)
        self.assertNotIn(self.client_address, output)
        self.assertNotIn(self.worker_address, output)
        self.assertNotIn(self.reviewer_address, output)
        self.assertNotIn('cmd-customer@example.test', output)
        self.assertNotIn('Private command test message', output)
        self.assertNotIn('Private command submission notes', output)
        self.assertNotIn('https://example.test/private-cmd-evidence', output)

        with self.assertRaises(CommandError):
            call_command('check_pilot_reliability', '--fail-on-attention', stdout=StringIO())
