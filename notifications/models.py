from django.db import models
from django.conf import settings


class Notification(models.Model):
    NOTIF_TYPES = [
        ("ORDER_NEW",       "New order placed"),
        ("ORDER_STATUS",    "Order status changed"),
        ("OFFER_RECEIVED",  "New offer received"),
        ("OFFER_ACCEPTED",  "Offer accepted"),
        ("OFFER_DECLINED",  "Offer declined"),
        ("REVIEW_RECEIVED", "New review received"),
        ("DEPOSIT_DONE",    "Deposit completed"),
        ("REFERRAL_BONUS",  "Referral bonus credited"),
    ]

    recipient   = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    notif_type  = models.CharField(max_length=30, choices=NOTIF_TYPES)
    title       = models.CharField(max_length=200)
    message     = models.TextField()
    url         = models.CharField(max_length=500, blank=True, help_text="Deep-link URL for this notification")
    is_read     = models.BooleanField(default=False, db_index=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"

    def __str__(self):
        return f"[{self.get_notif_type_display()}] → {self.recipient.username}: {self.title}"

    @classmethod
    def notify(cls, recipient, notif_type, title, message, url=""):
        """Convenience factory — skips self-notifications and duplicates within 5 s."""
        return cls.objects.create(
            recipient=recipient,
            notif_type=notif_type,
            title=title,
            message=message,
            url=url,
        )
