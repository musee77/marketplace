from django.db import models
from django.conf import settings

class SearchKeyword(models.Model):
    keyword = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True, help_text="Display on the homepage.")
    display_order = models.PositiveIntegerField(default=0, help_text="Order in which keywords are shown.")

    class Meta:
        ordering = ["display_order", "keyword"]

    def __str__(self):
        return self.keyword


class ContactMessage(models.Model):
    class Category(models.TextChoices):
        GENERAL = "GENERAL", "General Inquiry"
        ORDER_SUPPORT = "ORDER_SUPPORT", "Order & Project Support"
        SPECIALIST_HELP = "SPECIALIST_HELP", "Specialist / Analyst Help"
        BILLING = "BILLING", "Billing & Payments"
        BUG_REPORT = "BUG_REPORT", "Bug Report / Technical Issue"
        OTHER = "OTHER", "Other"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        RESOLVED = "RESOLVED", "Resolved"
        CLOSED = "CLOSED", "Closed"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="contact_messages",
        help_text="Linked user account if logged in at submission.",
    )
    name = models.CharField(max_length=120)
    email = models.EmailField()
    subject = models.CharField(max_length=200)
    category = models.CharField(
        max_length=30,
        choices=Category.choices,
        default=Category.GENERAL,
    )
    message = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    admin_notes = models.TextField(
        blank=True,
        help_text="Internal notes by managers/staff.",
    )
    admin_reply = models.TextField(
        blank=True,
        help_text="Official response sent back to the user.",
    )
    replied_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp of when the team replied.",
    )
    is_read_by_user = models.BooleanField(
        default=False,
        help_text="Whether the user has viewed the response.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Contact Message"
        verbose_name_plural = "Contact Messages"

    def __str__(self):
        return f"{self.subject} — {self.name} ({self.get_status_display()})"

