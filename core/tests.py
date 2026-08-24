from django.test import TestCase
from django.urls import reverse
from accounts.models import User, SpecialistProfile, ClientProfile
from services.models import Service, Category
from orders.models import Order


class DashboardPaginationTestCase(TestCase):
    def setUp(self):
        self.client_user = User.objects.create_user(
            username="testclient",
            email="client@example.com",
            password="password123",
            role=User.Role.CLIENT
        )
        ClientProfile.objects.get_or_create(user=self.client_user)

        self.specialist_user = User.objects.create_user(
            username="testspec",
            email="spec@example.com",
            password="password123",
            role=User.Role.SPECIALIST
        )
        sp, _ = SpecialistProfile.objects.get_or_create(user=self.specialist_user)
        sp.is_approved = True
        sp.save()

        self.category = Category.objects.create(name="AI Analytics", slug="ai-analytics")
        self.service = Service.objects.create(
            specialist=self.specialist_user,
            category=self.category,
            title="Data Science Service",
            slug="data-science-service",
            price=150
        )

        # Create 15 orders for the client
        for i in range(15):
            Order.objects.create(
                client=self.client_user,
                specialist=self.specialist_user,
                service=self.service,
                price=150,
                status=Order.Status.PENDING,
                is_paid=True
            )

    def test_dashboard_orders_pagination(self):
        self.client.login(username="testclient", password="password123")
        response = self.client.get(reverse("core:dashboard"))
        self.assertEqual(response.status_code, 200)

        page_obj = response.context["page_obj"]
        self.assertEqual(page_obj.paginator.per_page, 10)
        self.assertEqual(len(page_obj), 10)
        self.assertEqual(page_obj.paginator.num_pages, 2)
        self.assertFalse(page_obj.has_previous())
        self.assertTrue(page_obj.has_next())

        # Test page 2
        response_page2 = self.client.get(reverse("core:dashboard") + "?page=2")
        self.assertEqual(response_page2.status_code, 200)
        page_obj2 = response_page2.context["page_obj"]
        self.assertEqual(len(page_obj2), 5)
        self.assertTrue(page_obj2.has_previous())
        self.assertFalse(page_obj2.has_next())

