import random
from datetime import timedelta

from celery import shared_task
from django.db import transaction
from django.utils import timezone

from orders.models import Order


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


@shared_task
def create_simulated_orders(count=10):
    """Create one weekly batch of demo orders spread across the last week."""
    count = max(1, min(int(count), 10))
    source_orders = list(
        Order.objects.filter(is_simulated=True, service__isnull=False)
        .select_related("service", "specialist", "client")
        .order_by("-created_at")[:50]
    )
    if not source_orders:
        return {"created": 0, "reason": "Run seed_data first."}

    created = 0
    now = timezone.now()
    week_seconds = 7 * 24 * 60 * 60
    with transaction.atomic():
        for _ in range(count):
            source = random.choice(source_orders)
            created_at = now - timedelta(seconds=random.randint(0, week_seconds))
            order = Order(
                service=source.service,
                client=source.client,
                specialist=source.specialist,
                status=random.choice(SIMULATED_STATUSES),
                requirements=random.choice(SIMULATED_REQUIREMENTS),
                price=source.service.price,
                due_date=(created_at + timedelta(days=source.service.delivery_days)).date(),
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

    return {"created": created}
