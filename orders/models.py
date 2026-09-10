from decimal import Decimal

from django.db import models
from django.conf import settings
from django.urls import reverse


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending acceptance"
        ACCEPTED = "ACCEPTED", "Accepted"
        IN_PROGRESS = "IN_PROGRESS", "In progress"
        DELIVERED = "DELIVERED", "Delivered"
        UNDER_REVISION = "UNDER_REVISION", "Under revision"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"
        DECLINED = "DECLINED", "Declined"

    service = models.ForeignKey("services.Service", on_delete=models.CASCADE, related_name="orders", null=True, blank=True,
                                help_text="The service being ordered. Can be null for offers.")
    client = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="orders_placed",
                                limit_choices_to={"role": "CLIENT"})
    specialist = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="orders_received",
                                    limit_choices_to={"role": "SPECIALIST"})
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    requirements = models.TextField(blank=True, help_text="What the client needs")
    STANDARD_FEE_RATE = Decimal("0.20")
    REFERRAL_CLIENT_RATE = Decimal("0.90")  # Referred clients pay 90% on their first order
    REFERRAL_FEE_RATE = Decimal("0.10")  # 10% platform fee on the discounted order
    REFERRAL_BONUS_RATE = Decimal("0.05")  # 5% of the discounted order goes to the referrer

    price = models.DecimalField(max_digits=9, decimal_places=2)
    platform_fee_rate = models.DecimalField(max_digits=4, decimal_places=2, default=Decimal("0.20"),
                                            help_text="Always 20% — platform commission")
    platform_fee = models.DecimalField(max_digits=9, decimal_places=2, default=0,
                                        help_text="Commission kept by the platform (before referral payout)")
    specialist_earnings = models.DecimalField(max_digits=9, decimal_places=2, default=0,
                                               help_text="Earnings paid out to the specialist")
    referrer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name="referral_orders", help_text="Referrer who invited the client")
    referral_bonus = models.DecimalField(max_digits=9, decimal_places=2, default=Decimal("0.00"),
                                         help_text="5% of the discounted first order credited to the referrer")
    referral_bonus_credited = models.BooleanField(default=False)
    referral_discount_applied = models.BooleanField(default=False)
    revision_note = models.TextField(blank=True, help_text="Client's revision instructions")
    delivery_note = models.TextField(blank=True, help_text="Specialist's delivery note")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    due_date = models.DateField(null=True, blank=True)
    # payment fields
    PAYMENT_METHODS = (
        ("CARD", "Card (Paystack)"),
        ("BALANCE", "Account balance"),
    )
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default="CARD")
    is_paid = models.BooleanField(default=False)
    paid_at = models.DateTimeField(null=True, blank=True)
    is_simulated = models.BooleanField(
        default=False,
        help_text="Marks demo data created by the seed command, not a real customer order.",
    )
    # If this order was created from a chat offer message, store the message PK here
    # so the Paystack callback can mark the offer ACCEPTED after payment succeeds.
    offer_message_id = models.IntegerField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        title = self.service.title if self.service else f"Custom Offer #{self.pk}"
        return f"Order #{self.pk} — {title} ({self.get_status_display()})"

    @property
    def display_title(self):
        if self.service:
            return self.service.title
        if self.requirements:
            return self.requirements[:50]
        return f"Custom Offer #{self.pk}"

    @property
    def has_referral_bonus(self):
        """True if a referral bonus will be credited on this order."""
        return self.referral_bonus > Decimal("0.00")


    def get_absolute_url(self):
        return reverse("orders:detail", kwargs={"pk": self.pk})

    # allowed forward transitions per actor
    CLIENT_ACTIONS = {
        Status.DELIVERED: [Status.COMPLETED],  # UNDER_REVISION handled by order_request_revision view
        Status.PENDING: [Status.CANCELLED],
    }
    SPECIALIST_ACTIONS = {
        Status.PENDING: [Status.ACCEPTED, Status.DECLINED],
        Status.ACCEPTED: [Status.IN_PROGRESS],
        Status.IN_PROGRESS: [Status.DELIVERED],
        Status.UNDER_REVISION: [Status.DELIVERED],
    }

    def compute_fees(self):
        """Populate platform_fee, platform_fee_rate, referral_bonus, and specialist_earnings.

                On the client's first referred order, the client pays 90% of the entered
                price, the platform keeps 10%, and the referrer receives 5% of the
                discounted price. Standard orders use the regular 20% platform fee.
        """
        # Determine if this is the client's first referred order
        is_first_referred = False
        if self.client and getattr(self.client, 'referred_by', None):
            has_other_paid = Order.objects.filter(
                client=self.client,
                is_paid=True,
                is_simulated=False,
            ).exclude(pk=self.pk).exists()
            if not has_other_paid:
                is_first_referred = True

        if is_first_referred:
            self.referrer = self.client.referred_by
            if not self.referral_discount_applied:
                self.price = (self.price * self.REFERRAL_CLIENT_RATE).quantize(Decimal("0.01"))
                self.referral_discount_applied = True
            self.platform_fee_rate = self.REFERRAL_FEE_RATE
        else:
            self.platform_fee_rate = self.STANDARD_FEE_RATE

        self.platform_fee = (self.price * self.platform_fee_rate).quantize(Decimal("0.01"))

        if is_first_referred:
            self.referral_bonus = (self.price * self.REFERRAL_BONUS_RATE).quantize(Decimal("0.01"))
            self.specialist_earnings = (self.price - self.platform_fee).quantize(Decimal("0.01"))
        else:
            self.referral_bonus = Decimal("0.00")
            self.specialist_earnings = (self.price - self.platform_fee).quantize(Decimal("0.01"))

    def credit_referral_reward(self):
        """Credit referral reward to the referrer when order is paid."""
        if self.is_paid and self.referrer and self.referral_bonus > Decimal("0.00") and not self.referral_bonus_credited:
            if hasattr(self.referrer, 'specialist_profile') and self.referrer.role == self.referrer.Role.SPECIALIST:
                prof = self.referrer.specialist_profile
                prof.balance = (prof.balance or Decimal("0.00")) + self.referral_bonus
                prof.save(update_fields=["balance"])
            elif hasattr(self.referrer, 'client_profile'):
                prof = self.referrer.client_profile
                prof.balance = (prof.balance or Decimal("0.00")) + self.referral_bonus
                prof.save(update_fields=["balance"])
            self.referral_bonus_credited = True
            self.save(update_fields=["referral_bonus_credited"])

    @property
    def is_reviewable(self):
        return self.status == self.Status.COMPLETED and not hasattr(self, "review")


class OrderDocument(models.Model):
    """A file shared on an order by its specialist or a manager."""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="documents")
    title = models.CharField(max_length=200)
    file = models.FileField(upload_to="order_documents/")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_order_documents",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} — Order #{self.order_id}"


class Offer(models.Model):
    """Specialist sends an offer directly to a client. Auto-approved, creates an Order when accepted."""
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        ACCEPTED = "ACCEPTED", "Accepted"
        DECLINED = "DECLINED", "Declined"
        EXPIRED = "EXPIRED", "Expired"

    specialist = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="offers_sent",
                                   limit_choices_to={"role": "SPECIALIST"})
    client = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="offers_received",
                               limit_choices_to={"role": "CLIENT"})
    title = models.CharField(max_length=200, help_text="What you're offering (e.g., 'Data Analysis Report')")
    description = models.TextField(help_text="Detailed description of your offer")
    price = models.DecimalField(max_digits=9, decimal_places=2, help_text="Your quoted price in USD")
    delivery_days = models.PositiveIntegerField(default=5, help_text="Days to complete the work")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    order = models.OneToOneField(Order, on_delete=models.SET_NULL, null=True, blank=True, related_name="created_from_offer",
                                 help_text="Auto-populated when offer is accepted")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(null=True, blank=True, help_text="When the offer expires (optional)")

    class Meta:
        ordering = ["-created_at"]
        unique_together = ["specialist", "client", "title"]  # Prevent duplicate offers

    def __str__(self):
        return f"Offer: {self.title} — {self.specialist.username} → {self.client.username} ({self.get_status_display()})"

    def get_absolute_url(self):
        return reverse("orders:offer_detail", kwargs={"pk": self.pk})
