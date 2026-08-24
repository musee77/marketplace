"""
Signal handlers for the notification system.

Each handler fires Notification.notify() for the right recipient when
a meaningful event happens in orders, chat (offers), reviews, or deposits.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.urls import reverse

from .models import Notification


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _url(viewname, **kwargs):
    """Return a URL string or '' if the reverse fails (e.g. during tests)."""
    try:
        return reverse(viewname, kwargs=kwargs)
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------

@receiver(post_save, sender="orders.Order")
def handle_order_save(sender, instance, created, **kwargs):
    order = instance

    # 1) New paid order → notify the specialist
    if created and order.is_paid:
        title_str = order.service.title if order.service else f"Custom Offer #{order.pk}"
        Notification.notify(
            recipient=order.specialist,
            notif_type="ORDER_NEW",
            title="New order received",
            message=f"{order.client.get_full_name() or order.client.username} placed an order for '{title_str}'.",
            url=_url("orders:detail", pk=order.pk),
        )
        return  # Don't double-fire ORDER_STATUS on creation

    if created:
        return  # Unpaid new order — no notification until payment confirmed

    # 2) Order becomes paid (payment confirmed after Paystack callback)
    update_fields = kwargs.get("update_fields") or []
    if "is_paid" in update_fields and order.is_paid:
        title_str = order.service.title if order.service else f"Custom Offer #{order.pk}"
        Notification.notify(
            recipient=order.specialist,
            notif_type="ORDER_NEW",
            title="New order received",
            message=f"{order.client.get_full_name() or order.client.username} placed an order for '{title_str}'.",
            url=_url("orders:detail", pk=order.pk),
        )

    # 3) Status changed → notify the OTHER party
    if "status" in update_fields:
        status_label = order.get_status_display()
        title_str = order.service.title if order.service else f"Custom Offer #{order.pk}"
        order_url = _url("orders:detail", pk=order.pk)

        # Determine who changed it and who to notify
        status = order.status
        from orders.models import Order as OrderModel

        if status in (OrderModel.Status.ACCEPTED, OrderModel.Status.IN_PROGRESS,
                      OrderModel.Status.DELIVERED, OrderModel.Status.DECLINED):
            # Specialist acted → notify client
            Notification.notify(
                recipient=order.client,
                notif_type="ORDER_STATUS",
                title=f"Order {status_label.lower()}",
                message=f"Your order for '{title_str}' has been {status_label.lower()} by the specialist.",
                url=order_url,
            )
        elif status in (OrderModel.Status.COMPLETED, OrderModel.Status.CANCELLED):
            # Client acted → notify specialist
            Notification.notify(
                recipient=order.specialist,
                notif_type="ORDER_STATUS",
                title=f"Order {status_label.lower()}",
                message=f"The order for '{title_str}' has been marked {status_label.lower()} by the client.",
                url=order_url,
            )

    # 4) Referral bonus credited → notify the referrer
    if "referral_bonus_credited" in update_fields and order.referral_bonus_credited and order.referrer:
        Notification.notify(
            recipient=order.referrer,
            notif_type="REFERRAL_BONUS",
            title="Referral bonus credited!",
            message=f"You earned ${order.referral_bonus} referral bonus from {order.client.get_full_name() or order.client.username}'s order.",
            url=_url("core:dashboard"),
        )


# ---------------------------------------------------------------------------
# Chat offer messages
# ---------------------------------------------------------------------------

@receiver(post_save, sender="chat.Message")
def handle_offer_message(sender, instance, created, **kwargs):
    msg = instance

    if msg.message_type != "OFFER":
        return

    update_fields = kwargs.get("update_fields") or []

    # New offer sent by specialist → notify the client
    if created:
        conversation = msg.conversation
        client = conversation.other_participant(msg.sender)
        if client is None:
            return
        Notification.notify(
            recipient=client,
            notif_type="OFFER_RECEIVED",
            title="New offer from a specialist",
            message=f"{msg.sender.get_full_name() or msg.sender.username} sent you an offer: '{msg.offer_title}' for ${msg.offer_price}.",
            url=_url("chat:conversation", pk=conversation.pk),
        )
        return

    # Offer status changed
    if "offer_status" in update_fields:
        specialist = msg.sender
        conversation = msg.conversation
        client = conversation.other_participant(specialist)

        if msg.offer_status == "ACCEPTED":
            Notification.notify(
                recipient=specialist,
                notif_type="OFFER_ACCEPTED",
                title="Your offer was accepted!",
                message=f"{client.get_full_name() if client else 'A client'} accepted your offer '{msg.offer_title}'.",
                url=_url("chat:conversation", pk=conversation.pk),
            )
        elif msg.offer_status == "DECLINED":
            Notification.notify(
                recipient=specialist,
                notif_type="OFFER_DECLINED",
                title="Your offer was declined",
                message=f"{client.get_full_name() if client else 'A client'} declined your offer '{msg.offer_title}'.",
                url=_url("chat:conversation", pk=conversation.pk),
            )


# ---------------------------------------------------------------------------
# Reviews
# ---------------------------------------------------------------------------

@receiver(post_save, sender="reviews.Review")
def handle_review_created(sender, instance, created, **kwargs):
    if not created:
        return
    review = instance
    Notification.notify(
        recipient=review.reviewee,
        notif_type="REVIEW_RECEIVED",
        title="New review received",
        message=f"{review.reviewer.get_full_name() or review.reviewer.username} left you a {review.rating}★ review.",
        url=_url("services:detail", slug=review.service.slug) if review.service else "",
    )


# ---------------------------------------------------------------------------
# Deposits
# ---------------------------------------------------------------------------

@receiver(post_save, sender="accounts.DepositTransaction")
def handle_deposit(sender, instance, created, **kwargs):
    tx = instance
    update_fields = kwargs.get("update_fields") or []

    if tx.status == "COMPLETED" and ("status" in update_fields or created):
        Notification.notify(
            recipient=tx.client.user,
            notif_type="DEPOSIT_DONE",
            title="Deposit successful",
            message=f"${tx.amount} has been added to your account balance.",
            url=_url("accounts:edit_profile"),
        )
