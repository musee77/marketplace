from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.urls import reverse


class User(AbstractUser):
    class Role(models.TextChoices):
        CLIENT = "CLIENT", "Client"
        SPECIALIST = "SPECIALIST", "Specialist"
        MANAGER = "MANAGER", "Manager"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.CLIENT)
    email = models.EmailField(unique=True, blank=False, help_text="Required for payments and notifications.")
    phone = models.CharField(max_length=30, blank=True)
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    is_suspended = models.BooleanField(default=False)
    referral_code = models.CharField(max_length=20, unique=True, blank=True, db_index=True)
    referred_by = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL, related_name="referrals")
    date_created = models.DateTimeField(auto_now_add=True)

    REQUIRED_FIELDS = ["email", "first_name", "last_name"]

    class Meta:
        ordering = ["-date_created"]

    @classmethod
    def generate_referral_code(cls):
        import uuid
        while True:
            code = f"REF{uuid.uuid4().hex[:6].upper()}"
            if not cls.objects.filter(referral_code=code).exists():
                return code

    def save(self, *args, **kwargs):
        if not self.referral_code:
            self.referral_code = self.generate_referral_code()
        super().save(*args, **kwargs)

    @property
    def is_client(self):
        return self.role == self.Role.CLIENT

    @property
    def is_specialist(self):
        return self.role == self.Role.SPECIALIST

    @property
    def is_manager(self):
        return self.role == self.Role.MANAGER or self.is_superuser

    @property
    def referral_count(self):
        return self.referrals.count()

    @property
    def referral_orders_count(self):
        return self.referral_orders.filter(is_paid=True).count()

    @property
    def referral_earnings_total(self):
        from decimal import Decimal
        from django.db.models import Sum
        total = self.referral_orders.filter(is_paid=True).aggregate(Sum("referral_bonus"))["referral_bonus__sum"]
        return total or Decimal("0.00")

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"


class SpecialistProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="specialist_profile")
    headline = models.CharField(max_length=150, blank=True, help_text="e.g. 'Senior Data Engineer'")
    bio = models.TextField(blank=True)
    skills = models.CharField(max_length=400, blank=True, help_text="Comma-separated, e.g. Python, SQL, Power BI, dbt")
    hourly_rate = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    years_experience = models.PositiveIntegerField(default=0)
    location = models.CharField(max_length=120, blank=True)
    is_approved = models.BooleanField(default=False, help_text="Approved by a manager to operate on the platform")
    is_verified = models.BooleanField(default=False, help_text="Verified by a manager")
    is_available = models.BooleanField(default=True)
    portfolio_url = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # Financials
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    PAYOUT_METHODS = (
        ("STRIPE", "Stripe (recommended)"),
        ("MPESA", "M-Pesa"),
        ("PAYPAL", "PayPal"),
        ("BANK", "Bank transfer"),
    )
    payout_method = models.CharField(max_length=20, choices=PAYOUT_METHODS, blank=True)
    payout_details = models.TextField(blank=True, help_text="JSON or human-readable payout details (account, email, etc.)")

    @property
    def average_rating(self):
        agg = self.user.reviews_received.aggregate(models.Avg("rating"))
        return round(agg["rating__avg"] or 0, 1)

    @property
    def review_count(self):
        return self.user.reviews_received.count()

    def __str__(self):
        return f"Specialist: {self.user.username}"

    def get_absolute_url(self):
        return reverse("accounts:specialist_public", kwargs={"pk": self.pk})


class ClientProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="client_profile")
    company_name = models.CharField(max_length=150, blank=True)
    bio = models.TextField(blank=True)
    location = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    # Billing / financials for clients
    billing_address = models.TextField(blank=True)
    default_payment_method = models.CharField(max_length=30, blank=True, help_text="e.g. CARD, MPESA, BALANCE, PAYPAL")
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"Client: {self.user.username}"


class DepositTransaction(models.Model):
    client = models.ForeignKey(ClientProfile, on_delete=models.CASCADE, related_name="deposits")
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])
    STATUS_CHOICES = (
        ("PENDING", "Pending"),
        ("COMPLETED", "Completed"),
        ("FAILED", "Failed"),
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    payment_method = models.CharField(max_length=30, blank=True)
    reference = models.CharField(max_length=200, blank=True, help_text="Optional payment reference")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Deposit {self.amount} to {self.client.user.username} ({self.status})"
