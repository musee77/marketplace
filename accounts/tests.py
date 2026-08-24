from unittest.mock import patch
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from .models import SpecialistProfile, ClientProfile, DepositTransaction


class AddFundsTest(TestCase):
	@patch("orders.paystack_api.PaystackAPI.initialize_payment")
	def test_add_funds_redirects_to_paystack(self, mock_init):
		mock_init.return_value = {"authorization_url": "https://checkout.paystack.com/test_url"}
		User = get_user_model()
		user = User.objects.create_user(username="cli", password="pass", role=User.Role.CLIENT)
		ClientProfile.objects.create(user=user)
		self.client.login(username="cli", password="pass")
		resp = self.client.post(
			reverse("accounts:add_funds"),
			{
				"amount": "20.00",
				"payment_method": "PAYSTACK",
			},
		)
		self.assertEqual(resp.status_code, 302)
		self.assertEqual(resp.url, "https://checkout.paystack.com/test_url")
		tx = DepositTransaction.objects.filter(client__user=user).first()
		self.assertIsNotNone(tx)
		self.assertEqual(tx.status, "PENDING")


class EditProfileSpecialistTabTest(TestCase):
	def setUp(self):
		User = get_user_model()
		self.specialist = User.objects.create_user(
			username="spec1",
			email="spec1@example.com",
			password="password123",
			role=User.Role.SPECIALIST,
			first_name="Jane",
			last_name="Doe",
		)
		self.sp_profile, _ = SpecialistProfile.objects.get_or_create(
			user=self.specialist,
			headline="Initial Headline",
			skills="Python, SQL",
			hourly_rate=75,
		)

		self.client_user = User.objects.create_user(
			username="cli1",
			email="cli1@example.com",
			password="password123",
			role=User.Role.CLIENT,
			first_name="John",
			last_name="Smith",
		)
		self.cl_profile, _ = ClientProfile.objects.get_or_create(user=self.client_user)

	def test_specialist_sees_account_sections_without_tabs(self):
		self.client.login(username="spec1", password="password123")
		resp = self.client.get(reverse("accounts:edit_profile"))
		self.assertEqual(resp.status_code, 200)
		self.assertContains(resp, "Account")
		self.assertContains(resp, "Financials")
		self.assertNotContains(resp, "Specialization Details")
		self.assertNotContains(resp, "panel-rankings")
		self.assertContains(resp, "Initial Headline")

	def test_specialist_reviews_have_separate_page(self):
		self.client.login(username="cli1", password="password123")
		resp = self.client.get(reverse("accounts:specialist_reviews", kwargs={"pk": self.sp_profile.pk}))
		self.assertEqual(resp.status_code, 200)
		self.assertContains(resp, "reviews")
		self.assertContains(resp, "Average rating")

	def test_client_does_not_see_specialization_tab(self):
		self.client.login(username="cli1", password="password123")
		resp = self.client.get(reverse("accounts:edit_profile"))
		self.assertEqual(resp.status_code, 200)
		self.assertNotContains(resp, "Specialization Details")
		self.assertNotContains(resp, "panel-specialization")

	def test_specialist_can_update_specialization_details_and_requires_approval(self):
		self.sp_profile.is_approved = True
		self.sp_profile.save()

		self.client.login(username="spec1", password="password123")
		resp = self.client.post(
			reverse("accounts:edit_profile"),
			{
				"submit_specialization": "1",
				"headline": "Lead Data Architect",
				"bio": "Experienced data architect with 10 years in data pipelines.",
				"skills": "Python, Snowflake, dbt, Spark",
				"hourly_rate": "120.00",
				"years_experience": "10",
				"location": "New York, USA",
				"portfolio_url": "https://example.com/portfolio",
				"is_available": "on",
			},
		)
		self.assertEqual(resp.status_code, 302)
		self.sp_profile.refresh_from_db()
		self.assertEqual(self.sp_profile.headline, "Lead Data Architect")
		self.assertEqual(self.sp_profile.skills, "Python, Snowflake, dbt, Spark")
		self.assertEqual(self.sp_profile.hourly_rate, 120.00)
		self.assertEqual(self.sp_profile.years_experience, 10)
		self.assertEqual(self.sp_profile.location, "New York, USA")
		self.assertEqual(self.sp_profile.portfolio_url, "https://example.com/portfolio")
		self.assertTrue(self.sp_profile.is_available)
		# Crucial check: is_approved is set to False pending manager review
		self.assertFalse(self.sp_profile.is_approved)

	def test_specialist_cannot_change_email_from_account_details(self):
		self.sp_profile.is_approved = True
		self.sp_profile.save()

		self.client.login(username="spec1", password="password123")
		resp = self.client.post(
			reverse("accounts:edit_profile"),
			{
				"submit_account": "1",
				"first_name": "Janet",
				"last_name": "Doe",
				"email": "janet.doe@example.com",
				"phone": "+1234567890",
			},
		)
		self.assertEqual(resp.status_code, 302)
		self.specialist.refresh_from_db()
		self.sp_profile.refresh_from_db()
		self.assertEqual(self.specialist.first_name, "Janet")
		self.assertEqual(self.specialist.email, "spec1@example.com")
		self.assertEqual(self.specialist.phone, "+1234567890")
		self.assertTrue(self.sp_profile.is_approved)

	def test_specialist_sees_financials_tab(self):
		self.client.login(username="spec1", password="password123")
		resp = self.client.get(reverse("accounts:edit_profile"))
		self.assertEqual(resp.status_code, 200)
		self.assertContains(resp, "Financials")
		self.assertContains(resp, "panel-financials")
		self.assertContains(resp, "payout_method")

	def test_client_does_not_see_financials_tab(self):
		self.client.login(username="cli1", password="password123")
		resp = self.client.get(reverse("accounts:edit_profile"))
		self.assertEqual(resp.status_code, 200)
		self.assertNotContains(resp, "Financials")
		self.assertNotContains(resp, "panel-financials")

	def test_specialist_can_update_financials(self):
		self.client.login(username="spec1", password="password123")
		resp = self.client.post(
			reverse("accounts:edit_profile"),
			{
				"submit_financials": "1",
				"payout_method": "PAYPAL",
				"payout_details": "spec1@paypal.com",
			},
		)
		self.assertEqual(resp.status_code, 302)
		self.sp_profile.refresh_from_db()
		self.assertEqual(self.sp_profile.payout_method, "PAYPAL")
		self.assertEqual(self.sp_profile.payout_details, "spec1@paypal.com")



