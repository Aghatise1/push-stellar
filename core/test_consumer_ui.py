from datetime import timedelta

from django.contrib.staticfiles.storage import staticfiles_storage
from django.contrib.staticfiles import finders
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import Assignment, Job, Message, StaffAccess, SupportTicket, User


class ConsumerShellTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        accepted = timezone.now()
        cls.member = User.objects.create_user(
            username="member@example.test",
            email="member@example.test",
            password="Independent-cobalt-732!",
            display_name="Push Member",
            email_verified=True,
            terms_version="2026-10-06.1",
            terms_accepted_at=accepted,
        )
        cls.staff = User.objects.create_user(
            username="staff@example.test",
            email="staff@example.test",
            password="Independent-cobalt-732!",
            display_name="Push Owner",
            email_verified=True,
            terms_version="2026-10-06.1",
            terms_accepted_at=accepted,
            is_staff=True,
        )
        StaffAccess.objects.create(
            user=cls.staff,
            role="owner",
            status="approved",
            approved_at=accepted,
        )

    def test_customer_shell_is_scoped_away_from_staff_and_public_pages(self):
        self.client.force_login(self.member)
        customer = self.client.get(reverse("workspace"))
        self.assertContains(customer, 'class="app-mode customer-app-mode"')
        self.assertContains(customer, staticfiles_storage.url("customer-app.css"))

        self.client.logout()
        self.client.force_login(self.staff)
        staff = self.client.get(reverse("owner_dashboard"))
        self.assertNotContains(staff, "customer-app-mode")
        self.assertNotContains(staff, "customer-app.css")

        self.client.logout()
        public = self.client.get(reverse("home"))
        self.assertNotContains(public, "customer-app-mode")
        self.assertNotContains(public, "customer-app.css")

    def test_customer_navigation_stays_stable_without_conversations(self):
        self.client.force_login(self.member)
        response = self.client.get(reverse("workspace"))
        self.assertContains(response, 'class="customer-primary-nav"')
        self.assertContains(response, 'class="customer-more-menu"')
        self.assertContains(response, 'class="mobile-dock customer-mobile-dock"')
        for label in ("Home", "Work", "Find", "Messages", "Account"):
            self.assertContains(response, f"<span>{label}</span>")
        self.assertContains(response, reverse("inbox"))


class ConsumerHomeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        accepted = timezone.now()
        common = {
            "password": "Independent-cobalt-732!",
            "email_verified": True,
            "terms_version": "2026-10-06.1",
            "terms_accepted_at": accepted,
        }
        cls.client_user = User.objects.create_user(
            username="client@example.test",
            email="client@example.test",
            display_name="Maya Client",
            **common,
        )
        cls.worker = User.objects.create_user(
            username="worker@example.test",
            email="worker@example.test",
            display_name="Noah Worker",
            **common,
        )

    def make_assignment(self, status):
        job = Job.objects.create(
            owner=self.client_user,
            project="Launch",
            title=f"{status.replace('_', ' ').title()} project",
            description="Create a focused product experience.",
            deliverables="A tested interface.",
            acceptance_criteria="Matches the agreed brief.",
            category="UI/UX Design",
            payment_asset="XLM",
            budget=50,
            deadline=timezone.localdate() + timedelta(days=14),
            status="assigned",
            moderation_status="approved",
        )
        return Assignment.objects.create(
            job=job,
            worker=self.worker,
            scope=job.deliverables,
            budget=job.budget,
            status=status,
            escrow_required=True,
            agreement_snapshot={"payment_asset": "XLM"},
        )

    def priority_for(self, user):
        self.client.force_login(user)
        response = self.client.get(reverse("workspace"))
        self.assertEqual(response.status_code, 200)
        return response, response.context["workspace_priority"]

    def test_client_is_prompted_to_fund_an_accepted_agreement(self):
        assignment = self.make_assignment("awaiting_funding")
        response, priority = self.priority_for(self.client_user)
        self.assertEqual(priority["kind"], "fund_agreement")
        self.assertIn("fund", priority["title"].lower())
        self.assertEqual(priority["url"], reverse("assignment", args=[assignment.pk]))
        self.assertContains(response, 'data-priority-kind="fund_agreement"')

    def test_worker_sees_that_client_funding_is_still_pending(self):
        self.make_assignment("awaiting_funding")
        _, priority = self.priority_for(self.worker)
        self.assertEqual(priority["kind"], "waiting_for_funding")
        self.assertIn("client", priority["body"].lower())
        self.assertNotIn("fund now", priority["action_label"].lower())

    def test_worker_is_prompted_to_review_an_unaccepted_agreement(self):
        assignment = self.make_assignment("awaiting_acceptance")
        _, priority = self.priority_for(self.worker)
        self.assertEqual(priority["kind"], "review_agreement")
        self.assertEqual(priority["url"], reverse("assignment", args=[assignment.pk]))
        self.assertIn("review", priority["action_label"].lower())

    def test_client_is_prompted_to_review_submitted_work(self):
        self.make_assignment("submitted")
        _, priority = self.priority_for(self.client_user)
        self.assertEqual(priority["kind"], "review_delivery")
        self.assertIn("delivery", priority["title"].lower())

    def test_member_without_active_work_gets_a_clear_starting_action(self):
        response, priority = self.priority_for(self.worker)
        self.assertEqual(priority["kind"], "find_work")
        self.assertEqual(priority["url"], reverse("jobs"))
        self.assertContains(response, 'class="consumer-priority-action button"', count=1)

    def test_home_uses_compact_work_messages_and_wallet_sections(self):
        self.make_assignment("funded")
        response, _ = self.priority_for(self.worker)
        self.assertContains(response, 'class="consumer-home-grid"')
        self.assertContains(response, 'data-home-section="active-work"')
        self.assertContains(response, 'data-home-section="messages"')
        self.assertContains(response, 'data-home-section="wallet"')
        self.assertNotContains(response, "hero-balance")
        self.assertNotContains(response, "payment-motion")

    def test_active_work_is_selected_before_the_four_item_limit(self):
        active = self.make_assignment("funded")
        for _ in range(4):
            self.make_assignment("paid")
        response, _ = self.priority_for(self.worker)
        self.assertIn(active, response.context["active_assignments"])

    def test_closed_work_shows_the_active_work_empty_state(self):
        self.make_assignment("paid")
        response, _ = self.priority_for(self.worker)
        self.assertContains(response, "No active work yet")

    def test_legacy_records_do_not_claim_escrow_funding(self):
        item = self.make_assignment("funded")
        item.escrow_required = False
        item.save(update_fields=["escrow_required"])
        _, priority = self.priority_for(self.worker)
        self.assertEqual(priority["kind"], "find_work")


class ConsumerWorkTests(ConsumerHomeTests):
    def test_work_hub_uses_a_stable_segmented_control_and_record_cards(self):
        self.make_assignment("awaiting_acceptance")
        self.client.force_login(self.worker)
        response = self.client.get(reverse("work"))
        self.assertContains(response, "consumer-segmented-nav")
        for view in ("assigned", "applications", "hiring", "posted"):
            self.assertContains(response, f"?view={view}")
        self.assertContains(response, "consumer-work-card")
        self.assertContains(response, "Awaiting agreement")

    def test_hiring_view_keeps_agreement_link_budget_and_status(self):
        assignment = self.make_assignment("awaiting_funding")
        self.client.force_login(self.client_user)
        response = self.client.get(reverse("work") + "?view=hiring")
        self.assertContains(response, reverse("assignment", args=[assignment.pk]))
        self.assertContains(response, assignment.budget_display)
        self.assertContains(response, assignment.get_status_display())


class ConsumerJobsTests(ConsumerHomeTests):
    def test_job_card_shows_client_scope_budget_and_primary_action(self):
        assignment = self.make_assignment("awaiting_acceptance")
        assignment.delete()
        assignment.job.status = "open"
        assignment.job.save(update_fields=["status"])
        self.client.force_login(self.worker)
        response = self.client.get(reverse("jobs"))
        self.assertContains(response, 'class="consumer-job-card')
        self.assertContains(response, assignment.job.owner.display_name)
        self.assertContains(response, assignment.job.description)
        self.assertContains(response, assignment.job.budget_display)
        self.assertContains(response, reverse("job_detail", args=[assignment.job.pk]))

    def test_job_detail_and_forms_use_consumer_components_without_changing_actions(self):
        assignment = self.make_assignment("awaiting_acceptance")
        assignment.delete()
        job = assignment.job
        job.status = "open"
        job.save(update_fields=["status"])
        self.client.force_login(self.worker)

        detail = self.client.get(reverse("job_detail", args=[job.pk]))
        self.assertContains(detail, 'class="consumer-job-detail')
        self.assertContains(detail, f'action="{reverse("apply", args=[job.pk])}"')
        self.assertContains(detail, "csrfmiddlewaretoken")

        create = self.client.get(reverse("job_create"))
        self.assertContains(create, 'class="consumer-form-page')
        self.assertContains(create, "csrfmiddlewaretoken")
        self.assertContains(create, "Deliverables")


class ConsumerWorkroomTests(ConsumerHomeTests):
    @override_settings(PUSH_TESTNET_ONLY=False)
    def test_worker_sees_one_primary_agreement_action_and_current_status(self):
        assignment = self.make_assignment("awaiting_acceptance")
        assignment.escrow_required = False
        assignment.save(update_fields=["escrow_required"])
        self.client.force_login(self.worker)
        response = self.client.get(reverse("assignment", args=[assignment.pk]))
        self.assertContains(response, "consumer-workroom")
        self.assertContains(response, assignment.get_status_display())
        self.assertContains(response, "consumer-primary-action", count=1)
        self.assertContains(response, "Cancel this agreement")

    def test_escrow_workroom_keeps_wallet_and_transaction_hooks(self):
        assignment = self.make_assignment("awaiting_acceptance")
        self.client.force_login(self.client_user)
        response = self.client.get(reverse("assignment", args=[assignment.pk]))
        self.assertContains(response, "consumer-workroom")
        self.assertContains(response, "consumer-progress")
        self.assertContains(response, "data-wallet-connect")
        self.assertContains(response, "data-escrow-room")
        self.assertContains(response, "data-escrow-status")
        self.assertContains(response, "data-escrow-retry")

    def test_messages_keep_project_context_privacy_and_composer(self):
        assignment = self.make_assignment("funded")
        Message.objects.create(assignment=assignment, sender=self.client_user, body="The scope is confirmed.")
        self.client.force_login(self.worker)
        response = self.client.get(reverse("conversation", args=[assignment.pk]))
        self.assertContains(response, "consumer-chat")
        self.assertContains(response, "consumer-chat-composer")
        self.assertContains(response, assignment.job.title)
        self.assertContains(response, "does not currently provide end-to-end encryption")
        self.assertContains(response, f'action="{reverse("conversation", args=[assignment.pk])}"')

    def test_closed_conversation_remains_visible_and_read_only(self):
        assignment = self.make_assignment("paid")
        Message.objects.create(assignment=assignment, sender=self.client_user, body="Payment released.")
        self.client.force_login(self.worker)
        response = self.client.get(reverse("conversation", args=[assignment.pk]))
        self.assertContains(response, "read-only")
        self.assertNotContains(response, "consumer-chat-composer")


class ConsumerWalletTests(ConsumerHomeTests):
    wallet_address = "GAOLY6ZLXM4V5NOFFHWX7QYNZR4MECF2AECJSHBDFBFEG4T4OZOTQZTR"

    def wallet_response(self, user=None):
        self.client.force_login(user or self.worker)
        response = self.client.get(reverse("wallet"))
        self.assertEqual(response.status_code, 200)
        return response

    def test_wallet_separates_receiving_session_and_escrow_states(self):
        response = self.wallet_response()
        self.assertContains(response, "consumer-wallet-states")
        self.assertContains(response, "Receiving address")
        self.assertContains(response, "Freighter session")
        self.assertContains(response, "Escrow payments")
        self.assertContains(response, "No address saved")
        self.assertContains(response, "Freighter disconnected")
        self.assertContains(response, "Stellar testnet")
        self.assertContains(response, "data-wallet-connect")
        self.assertContains(response, "data-wallet-status")

    def test_saved_address_is_not_described_as_a_live_connection(self):
        self.worker.stellar_address = self.wallet_address
        self.worker.save(update_fields=["stellar_address"])
        response = self.wallet_response()
        self.assertContains(response, "Saved for receiving")
        self.assertContains(response, "Freighter disconnected")
        self.assertContains(response, self.wallet_address)

    def test_matching_session_is_labelled_connected_on_testnet(self):
        self.worker.stellar_address = self.wallet_address
        self.worker.save(update_fields=["stellar_address"])
        self.client.force_login(self.worker)
        session = self.client.session
        session["wallet_connected_address"] = self.wallet_address
        session.save()
        response = self.client.get(reverse("wallet"))
        self.assertContains(response, "Connected on testnet")
        self.assertContains(response, "Disconnect")

    def test_payments_use_compact_evidence_records(self):
        response = self.wallet_response()
        payments = self.client.get(reverse("payments"))
        self.assertContains(payments, "consumer-payment-summary")
        self.assertContains(payments, "consumer-payment-history")
        self.assertContains(payments, "Testnet assets have no monetary value")


class ConsumerRemainingPagesTests(ConsumerHomeTests):
    def assert_standard_page(self, route_name, marker):
        self.client.force_login(self.worker)
        response = self.client.get(reverse(route_name))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "consumer-standard-page")
        self.assertContains(response, marker)
        return response

    def test_notifications_account_profile_and_analytics_share_the_system(self):
        self.assert_standard_page("notifications", "consumer-list-group")
        settings = self.assert_standard_page("account_settings", "consumer-settings-groups")
        self.assertContains(settings, "consumer-danger-group")
        self.assertContains(settings, reverse("request_account_deletion"))
        for route in ("wallet", "payments", "support", "community", "analytics"):
            self.assertContains(settings, f'href="{reverse(route)}"')
        self.assert_standard_page("profile", "consumer-form-surface")
        self.assert_standard_page("analytics", "consumer-metric-group")

    def test_support_keeps_ticket_creation_state_and_feedback_routes(self):
        support = self.assert_standard_page("support", "consumer-support-page")
        self.assertContains(support, "csrfmiddlewaretoken")
        ticket = SupportTicket.objects.create(
            requester=self.worker,
            subject="Wallet connection help",
            category="payment",
            description="The wallet state needs review.",
            status="resolved",
        )
        detail = self.client.get(reverse("support_ticket", args=[ticket.pk]))
        self.assertContains(detail, "consumer-standard-page")
        self.assertContains(detail, ticket.get_status_display())
        self.assertContains(detail, reverse("support_feedback", args=[ticket.pk]))

    def test_community_list_detail_and_form_keep_moderation_actions(self):
        community = self.assert_standard_page("community", "consumer-community-page")
        self.assertContains(community, reverse("community_create"))
        create = self.client.get(reverse("community_create"))
        self.assertContains(create, "consumer-standard-page")
        self.assertContains(create, "csrfmiddlewaretoken")


class ConsumerMotionTests(ConsumerShellTests):
    def test_customer_motion_is_scoped_away_from_staff_and_public_pages(self):
        self.client.force_login(self.member)
        customer = self.client.get(reverse("workspace"))
        self.assertContains(customer, staticfiles_storage.url("customer-motion.js"))
        self.assertContains(customer, 'class="customer-primary-nav"')

        self.client.logout()
        self.client.force_login(self.staff)
        staff = self.client.get(reverse("owner_dashboard"))
        self.assertNotContains(staff, "customer-motion.js")

        self.client.logout()
        public = self.client.get(reverse("home"))
        self.assertNotContains(public, "customer-motion.js")

    def test_customer_styles_define_motion_ready_and_reduced_motion_states(self):
        css_path = finders.find("customer-app.css")
        self.assertIsNotNone(css_path)
        css = open(css_path, encoding="utf-8").read()
        self.assertIn(".customer-motion-ready", css)
        self.assertIn("prefers-reduced-motion:reduce", css)
        self.assertIn("@media(hover:hover)and(pointer:fine)", css.replace(" ", ""))

