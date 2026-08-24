from django.db import models
from django.db.models import Count, Q
from django.conf import settings


class ConversationManager(models.Manager):
    def get_or_create_between(self, user1, user2):
        """Get or create a conversation between two users."""
        # Find conversation containing both users (order-independent)
        # A conversation exists if it has exactly these two participants
        existing = self.annotate(
            participant_count=Count('participants')
        ).filter(
            participants=user1,
            participant_count=2
        )
        
        for conv in existing:
            if conv.participants.filter(pk=user2.pk).exists():
                return conv, False  # Found existing conversation
        
        # Create new conversation
        conversation = self.create()
        conversation.participants.add(user1, user2)
        return conversation, True  # Newly created


class Conversation(models.Model):
    """A conversation thread between two users."""
    participants = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="conversations")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    objects = ConversationManager()

    class Meta:
        ordering = ["-updated_at"]

    def other_participant(self, user):
        return self.participants.exclude(pk=user.pk).first()

    def last_message(self):
        return self.messages.order_by("-created_at").first()

    def last_visible_message_for(self, user):
        return self.messages.filter(
            models.Q(is_approved=True) | models.Q(sender=user) | models.Q(message_type="OFFER")
        ).exclude(is_rejected=True, message_type="TEXT").order_by("-created_at").first()

    def __str__(self):
        names = ", ".join(u.get_full_name() or u.username for u in self.participants.all())
        return f"Conversation ({names})"


class Message(models.Model):
    """A single message in a conversation. Can be text or an offer (which auto-approves)."""
    MESSAGE_TYPE_CHOICES = (
        ("TEXT", "Text message"),
        ("OFFER", "Offer"),
    )
    
    OFFER_STATUS_CHOICES = (
        ("PENDING", "Pending"),
        ("ACCEPTED", "Accepted"),
        ("DECLINED", "Declined"),
    )
    
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_messages")
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPE_CHOICES, default="TEXT")
    
    # For text messages
    body = models.TextField(blank=True)
    
    # For offer messages
    offer_title = models.CharField(max_length=200, blank=True)
    offer_description = models.TextField(blank=True)
    offer_price = models.DecimalField(max_digits=9, decimal_places=2, null=True, blank=True)
    offer_delivery_days = models.PositiveIntegerField(null=True, blank=True)
    offer_status = models.CharField(max_length=20, choices=OFFER_STATUS_CHOICES, default="PENDING")
    offer_service = models.ForeignKey(
        "services.Service",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="offer_messages",
    )
    
    is_approved = models.BooleanField(default=False)
    is_rejected = models.BooleanField(default=False)
    is_read = models.BooleanField(default=False)
    # Optional file attachment
    attachment = models.FileField(upload_to="chat_attachments/", null=True, blank=True)
    attachment_name = models.CharField(max_length=255, blank=True, help_text="Original filename for display")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def save(self, *args, **kwargs):
        if not self.pk:
            # Offers are always auto-approved
            if self.message_type == "OFFER":
                self.is_approved = True
            # If the sender is not a specialist, automatically approve the message
            elif hasattr(self.sender, "role") and self.sender.role != "SPECIALIST":
                self.is_approved = True
        super().save(*args, **kwargs)

    def __str__(self):
        if self.message_type == "OFFER":
            return f"[Offer] {self.sender.username}: {self.offer_title}"
        status = "✓" if self.is_approved else ("✗" if self.is_rejected else "⏳")
        return f"[{status}] {self.sender.username}: {self.body[:50]}"


class SystemChatMessage(models.Model):
    """A persisted question or reply in the built-in system assistant."""
    ROLE_CHOICES = (
        ("USER", "User"),
        ("ASSISTANT", "Assistant"),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="system_chat_messages")
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    body = models.TextField(max_length=240)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.user.username} ({self.role}): {self.body[:50]}"
