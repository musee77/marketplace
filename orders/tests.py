from decimal import Decimal
from django.test import TestCase
from accounts.models import User, SpecialistProfile, ClientProfile
from services.models import Category, Service
from orders.models import Order


class ReferralFeeTestCase(TestCase):
    def setUp(self):
        # Create referrer
        self.referrer = User.objects.create_user(
            username="referrer",
            email="referrer@example.com",
            password="password123",
            role=User.Role.CLIENT
        )
        ClientProfile.objects.get_or_create(user=self.referrer)

        # Create referred client
        self.client_user = User.objects.create_user(
            username="testclient",
            email="client@example.com",
            password="password123",
            role=User.Role.CLIENT,
            referred_by=self.referrer
        )
        ClientProfile.objects.get_or_create(user=self.client_user)

        # Create specialist
        self.specialist_user = User.objects.create_user(
            username="testspec",
            email="spec@example.com",
            password="password123",
            role=User.Role.SPECIALIST
        )
        sp, _ = SpecialistProfile.objects.get_or_create(user=self.specialist_user)
        sp.is_approved = True
        sp.save()

        # Create category & service
        self.category = Category.objects.create(name="Data Engineering", slug="data-engineering")
        self.service = Service.objects.create(
            specialist=self.specialist_user,
            category=self.category,
            title="Pipeline Build",
            slug="pipeline-build",
            price=200
        )

    def test_referred_client_first_order_discount_and_referrer_bonus(self):
        # Create first order (not yet paid)
        order = Order(
            client=self.client_user,
            specialist=self.specialist_user,
            service=self.service,
            price=self.service.price,
            status=Order.Status.PENDING
        )
        # Compute fees before saving (as done in views)
        order.compute_fees()
        order.save()

        # Verify 10% discount: price should be 200 * 0.90 = 180
        self.assertEqual(order.price, Decimal("180.00"))

        # Verify platform fee: 10% of 180 = 18.00
        self.assertEqual(order.platform_fee, Decimal("18.00"))

        # Verify referral bonus: 5% of 180 = 9.00
        self.assertEqual(order.referral_bonus, Decimal("9.00"))

        # Verify specialist earnings: 180 - 18 = 162
        self.assertEqual(order.specialist_earnings, Decimal("162.00"))

        # Mark paid to simulate payment
        order.is_paid = True
        order.save()

        # Create second order
        order2 = Order(
            client=self.client_user,
            specialist=self.specialist_user,
            service=self.service,
            price=self.service.price,
            status=Order.Status.PENDING
        )
        order2.compute_fees()
        order2.save()

        # Verify standard price (no discount): 200
        self.assertEqual(order2.price, Decimal("200.00"))

        # Verify standard platform fee: 20% of 200 = 40.00
        self.assertEqual(order2.platform_fee, Decimal("40.00"))

        # Verify referral bonus: 0.00
        self.assertEqual(order2.referral_bonus, Decimal("0.00"))

        # Verify specialist earnings: 200 - 40 = 160
        self.assertEqual(order2.specialist_earnings, Decimal("160.00"))
