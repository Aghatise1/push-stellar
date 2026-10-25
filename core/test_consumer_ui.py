from django.contrib.staticfiles.storage import staticfiles_storage
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import StaffAccess, User


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

