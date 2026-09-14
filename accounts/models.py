from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.urls import reverse
from datetime import timedelta


class User(AbstractUser):
    class Role(models.TextChoices):
        CLIENT = "CLIENT", "Client"
        SPECIALIST = "SPECIALIST", "Specialist"
        EDITOR = "EDITOR", "Editor"
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
        return self.referral_orders.filter(is_paid=True, is_simulated=False).count()

    @property
    def referral_earnings_total(self):
        from decimal import Decimal
        from django.db.models import Sum
        total = self.referral_orders.filter(
            is_paid=True,
            is_simulated=False,
        ).aggregate(Sum("referral_bonus"))["referral_bonus__sum"]
        return total or Decimal("0.00")

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"


class SpecialistProfile(models.Model):
    class ApprovalStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="specialist_profile")
    headline = models.CharField(max_length=150, blank=True, help_text="e.g. 'Senior Data Engineer'")
    bio = models.TextField(blank=True)
    skills = models.CharField(max_length=400, blank=True, help_text="Comma-separated, e.g. Python, SQL, Power BI, dbt")
    hourly_rate = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    years_experience = models.PositiveIntegerField(default=0)
    location = models.CharField(max_length=120, blank=True)
    is_approved = models.BooleanField(default=False, help_text="Approved by a manager to operate on the platform")
    approval_status = models.CharField(max_length=20, choices=ApprovalStatus.choices, default=ApprovalStatus.PENDING)
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

    def missing_required_tests(self):
        missing = []
        for test in SpecialistTest.objects.filter(is_active=True):
            questions = list(test.questions.all())
            question_count = len(questions)
            attempt = self.user.test_attempts.filter(
                test=test,
                status=SpecialistTestAttempt.Status.ACCEPTED,
            ).first()
            has_all_responses = attempt and all(
                attempt.responses.get(str(question.pk), "")
                for question in questions
            )
            if question_count == 0 or not attempt or attempt.total_questions != question_count or not has_all_responses:
                missing.append(test.title)
        return missing

    @property
    def has_platform_access(self):
        if self.missing_required_tests():
            return False
        return SpecialistTest.objects.filter(is_active=True).exists() or self.is_approved

    def approve_after_assessments(self):
        if not self.missing_required_tests() and not self.is_approved:
            self.is_approved = True
            self.approval_status = self.ApprovalStatus.APPROVED
            self.save(update_fields=("is_approved", "approval_status", "updated_at"))

    def __str__(self):
        return f"Specialist: {self.user.username}"

    def get_absolute_url(self):
        return reverse("accounts:specialist_public", kwargs={"pk": self.pk})


class SpecialistTest(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return self.title


class SpecialistTestQuestion(models.Model):
    class QuestionType(models.TextChoices):
        MULTIPLE_CHOICE = "MULTIPLE_CHOICE", "Multiple choice"
        TEXT = "TEXT", "Text answer"

    test = models.ForeignKey(SpecialistTest, on_delete=models.CASCADE, related_name="questions")
    question_type = models.CharField(max_length=20, choices=QuestionType.choices, default=QuestionType.MULTIPLE_CHOICE)
    prompt = models.TextField()
    option_a = models.CharField(max_length=500, blank=True)
    option_b = models.CharField(max_length=500, blank=True)
    option_c = models.CharField(max_length=500, blank=True)
    option_d = models.CharField(max_length=500, blank=True)
    correct_option = models.CharField(
        max_length=1,
        blank=True,
        choices=(("A", "A"), ("B", "B"), ("C", "C"), ("D", "D")),
    )
    correct_answer = models.CharField(max_length=500, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "pk"]

    @property
    def option_choices(self):
        return (
            ("A", self.option_a),
            ("B", self.option_b),
            ("C", self.option_c),
            ("D", self.option_d),
        )

    def __str__(self):
        return f"{self.test}: question {self.pk}"


class SpecialistTestAttempt(models.Model):
    class Status(models.TextChoices):
        SUBMITTED = "SUBMITTED", "Submitted"
        ACCEPTED = "ACCEPTED", "Accepted"
        REJECTED = "REJECTED", "Rejected"

    specialist = models.ForeignKey(User, on_delete=models.CASCADE, related_name="test_attempts")
    test = models.ForeignKey(SpecialistTest, on_delete=models.CASCADE, related_name="attempts")
    score = models.PositiveIntegerField(default=0)
    total_questions = models.PositiveIntegerField(default=0)
    attempt_number = models.PositiveIntegerField(default=1)
    responses = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SUBMITTED)
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="reviewed_test_attempts")

    class Meta:
        ordering = ["-submitted_at"]

    @property
    def percentage(self):
        if not self.total_questions:
            return 0
        return round(self.score * 100 / self.total_questions)

    @property
    def retake_number(self):
        return max(self.attempt_number - 1, 0)

    @property
    def next_retake_at(self):
        if self.status != self.Status.REJECTED or self.retake_number >= 3:
            return None
        wait_days = (0, 30, 90)[self.retake_number]
        return (self.reviewed_at or self.submitted_at) + timedelta(days=wait_days)

    def __str__(self):
        return f"{self.specialist.username} - {self.test.title} ({self.status})"


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
