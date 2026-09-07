import random
from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from accounts.models import User
from orders.models import Order
from services.models import Service


class Command(BaseCommand):
    help = "Create at most one simulated order when a random weekly slot is due."

    statuses = (
        Order.Status.PENDING,
        Order.Status.ACCEPTED,
        Order.Status.IN_PROGRESS,
        Order.Status.DELIVERED,
        Order.Status.COMPLETED,
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=5,
            help="Number of simulated orders to maintain this week (maximum 5).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would be created without writing orders.",
        )

    def handle(self, *args, **options):
        requested_count = options["count"]
        if requested_count < 1 or requested_count > 5:
            raise CommandError("--count must be between 1 and 5.")

        now = timezone.now()
        week_key = now.strftime("%G-W%V")
        marker = f"[weekly-simulation:{week_key}]"
        existing_count = Order.objects.filter(requirements__startswith=marker).count()
        missing_count = max(requested_count - existing_count, 0)

        if missing_count == 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Weekly simulation {week_key} already has {existing_count} orders; nothing to create."
                )
            )
            return

        if Order.objects.filter(
            requirements__startswith=marker,
            created_at__date=now.date(),
        ).exists():
            self.stdout.write(
                f"Weekly simulation {week_key} already created an order today; "
                "waiting for the next scheduled run."
            )
            return

        # Keep the same five random weekdays for the whole week so repeated
        # daily scheduler runs do not move or duplicate scheduled slots.
        scheduled_days = sorted(
            random.Random(week_key).sample(range(7), requested_count)
        )
        current_day = now.weekday()
        due_slots = [day for day in scheduled_days if day <= current_day]
        if len(due_slots) <= existing_count:
            next_slot = scheduled_days[existing_count]
            self.stdout.write(
                f"Weekly simulation {week_key}: next order is scheduled for "
                f"{(now + timedelta(days=next_slot - current_day)).date()}."
            )
            return

        clients = list(
            User.objects.filter(role=User.Role.CLIENT, is_active=True).order_by("pk")
        )
        services = list(
            Service.objects.filter(is_active=True, specialist__role=User.Role.SPECIALIST)
            .select_related("specialist")
            .order_by("pk")
        )
        if not clients:
            raise CommandError("No active client users are available for simulation.")
        if not services:
            raise CommandError("No active specialist services are available for simulation.")

        sequence = existing_count
        service = services[sequence % len(services)]
        client = clients[sequence % len(clients)]
        if client.pk == service.specialist_id:
            client = clients[(sequence + 1) % len(clients)]

        status = self.statuses[sequence % len(self.statuses)]
        order = Order(
            service=service,
            client=client,
            specialist=service.specialist,
            status=status,
            requirements=(
                f"{marker} Simulated weekly marketplace order. "
                "Use this record for dashboard and workflow testing."
            ),
            price=service.price,
            due_date=(now + timedelta(days=service.delivery_days)).date(),
            is_paid=True,
            paid_at=now,
            delivery_note=(
                "Simulated delivery ready for review."
                if status == Order.Status.DELIVERED
                else ""
            ),
        )

        if options["dry_run"]:
            self.stdout.write(
                f"Dry run: would create one order for {week_key} "
                f"(scheduled weekday {scheduled_days[sequence]})."
            )
            return

        with transaction.atomic():
            order.compute_fees()
            order.save()

        self.stdout.write(
            self.style.SUCCESS(
                f"Created one simulated order for {week_key}; "
                f"weekly total is {existing_count + 1}."
            )
        )
