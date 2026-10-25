from datetime import timedelta

from django.contrib.staticfiles.storage import staticfiles_storage
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Assignment, Job, StaffAccess, User


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

