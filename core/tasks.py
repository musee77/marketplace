import random
from datetime import timedelta

from celery import shared_task
from django.db import transaction
from django.utils import timezone

from accounts.models import User
from orders.models import Order
from services.models import Service


SIMULATED_REQUIREMENTS = (
    "Demo request for an analytics delivery.",
    "Sample marketplace order for the public progress feed.",
    "Simulated project brief for demonstration purposes.",
)
SIMULATED_STATUSES = (
    Order.Status.PENDING,
    Order.Status.ACCEPTED,
    Order.Status.IN_PROGRESS,
    Order.Status.DELIVERED,
)
SIMULATED_NEXT_STATUS = {
    Order.Status.PENDING: Order.Status.ACCEPTED,
    Order.Status.ACCEPTED: Order.Status.IN_PROGRESS,
    Order.Status.IN_PROGRESS: Order.Status.DELIVERED,
    Order.Status.DELIVERED: Order.Status.COMPLETED,
}


def _advance_simulated_orders():
    advanced = 0
    simulated_orders = Order.objects.filter(
        is_simulated=True,
        status__in=SIMULATED_NEXT_STATUS,
    )
    for order in simulated_orders.only("status"):
        order.status = SIMULATED_NEXT_STATUS[order.status]
        order.save(update_fields=("status", "updated_at"))
        advanced += 1
    return advanced


@shared_task
def advance_simulated_orders():
    """Move each simulated order one valid step forward."""
    return {"advanced": _advance_simulated_orders()}


@shared_task
def create_simulated_orders(count=10):
    """Create one weekly batch of demo orders spread across the last week."""
    count = max(1, min(int(count), 10))
    advanced = _advance_simulated_orders()
    source_orders = list(
        Order.objects.filter(is_simulated=True, service__isnull=False)
        .select_related("service", "specialist", "client")
        .order_by("-created_at")[:50]
    )
    if not source_orders:
        clients = list(
            User.objects.filter(role=User.Role.CLIENT, is_active=True).order_by("pk")
        )
        services = list(
            Service.objects.filter(
                is_active=True,
                specialist__role=User.Role.SPECIALIST,
            ).select_related("specialist").order_by("pk")[:50]
        )
        if not clients or not services:
            return {
                "created": 0,
                "advanced": advanced,
                "reason": "Active clients and services are required.",
            }
        source_orders = [
            (service, client)
            for service in services
            for client in clients
            if client.pk != service.specialist_id
        ]
        if not source_orders:
            return {
                "created": 0,
                "advanced": advanced,
                "reason": "A client different from the specialist is required.",
            }

    created = 0
    now = timezone.now()
    week_seconds = 7 * 24 * 60 * 60
    with transaction.atomic():
        for _ in range(count):
            source = random.choice(source_orders)
            if isinstance(source, tuple):
                service, client = source
                specialist = service.specialist
            else:
                service = source.service
                client = source.client
                specialist = source.specialist
            created_at = now - timedelta(seconds=random.randint(0, week_seconds))
            order = Order(
                service=service,
                client=client,
                specialist=specialist,
                status=random.choice(SIMULATED_STATUSES),
                requirements=random.choice(SIMULATED_REQUIREMENTS),
                price=service.price,
                due_date=(created_at + timedelta(days=service.delivery_days)).date(),
                is_simulated=True,
                is_paid=True,
                paid_at=created_at,
            )
            order.compute_fees()
            order.save()
            Order.objects.filter(pk=order.pk).update(
                created_at=created_at,
                updated_at=created_at,
            )
            created += 1

    return {"created": created, "advanced": advanced}
