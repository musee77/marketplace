from django.test import TestCase
from django.urls import reverse
from accounts.models import User, SpecialistProfile
from services.models import Service, Category


class ServicePaginationTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testspecialist",
            email="test@example.com",
            password="password123",
            role=User.Role.SPECIALIST
        )
        self.profile, _ = SpecialistProfile.objects.get_or_create(user=self.user)
        self.profile.is_approved = True
        self.profile.save()

        self.category = Category.objects.create(name="Data Science", slug="data-science")

        # Create 15 active services
        for i in range(15):
            Service.objects.create(
                specialist=self.user,
                category=self.category,
                title=f"Service Listing {i}",
                slug=f"service-listing-{i}",
                description="Sample description",
                price=100 + i,
                is_active=True,
            )

    def test_service_list_pagination_limit(self):
        response = self.client.get(reverse("services:list"))
        self.assertEqual(response.status_code, 200)
        page_obj = response.context["page_obj"]
        self.assertEqual(page_obj.paginator.per_page, 10)
        self.assertEqual(len(page_obj), 10)
        self.assertEqual(page_obj.paginator.num_pages, 2)

