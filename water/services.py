import uuid
from datetime import datetime, time

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .models import (
    Gallon,
    Participant,
    PaymentStatusHistory,
    WaterOrder,
)


def _purchase_datetime(purchase_date):
    value = datetime.combine(purchase_date, time.min)
    return timezone.make_aware(value)


@transaction.atomic
def create_mixed_water_order(
    participant,
    purchase_date,
    blue_quantity,
    blue_unit_price,
    pink_quantity,
    pink_unit_price,
    payment_status=Gallon.PaymentStatus.NOT_PAID,
    due_date=None,
    notes=""
):
    if blue_quantity + pink_quantity < 1:
        raise ValidationError(
            "Enter at least one blue or pink gallon."
        )

    if (
        payment_status == Gallon.PaymentStatus.WILL_BE_PAID
        and not due_date
    ):
        raise ValidationError(
            "A due date is required."
        )

    order = WaterOrder.objects.create(
        participant=participant,
        order_number=f"ORD-{uuid.uuid4().hex[:10].upper()}",
        distributed_at=_purchase_datetime(purchase_date),
        notes=notes
    )

    gallon_details = (
        (Gallon.GallonColor.BLUE, blue_quantity, blue_unit_price),
        (Gallon.GallonColor.PINK, pink_quantity, pink_unit_price),
    )
    sequence_number = 1

    for color, quantity, unit_price in gallon_details:
        for _ in range(quantity):
            gallon = Gallon.objects.create(
                order=order,
                sequence_number=sequence_number,
                color=color,
                unit_price=unit_price,
                payment_status=payment_status,
                due_date=due_date,
                paid_at=(
                    timezone.now()
                    if payment_status == Gallon.PaymentStatus.PAID
                    else None
                )
            )
            PaymentStatusHistory.objects.create(
                gallon=gallon,
                old_status="",
                new_status=payment_status,
                note="Initial payment status"
            )
            sequence_number += 1

    return order


@transaction.atomic
def create_water_order(
    participant_id,
    quantity,
    unit_price,
    gallon_color=Gallon.GallonColor.BLUE,
    payment_status=Gallon.PaymentStatus.NOT_PAID,
    due_date=None,
    notes=""
):
    if quantity < 1:
        raise ValidationError(
            "Quantity must be at least one."
        )

    if unit_price < 0:
        raise ValidationError(
            "Unit price cannot be negative."
        )

    valid_colors = {
        choice[0]
        for choice in Gallon.GallonColor.choices
    }

    if gallon_color not in valid_colors:
        raise ValidationError(
            "Gallon color must be BLUE or PINK."
        )

    if (
        payment_status == Gallon.PaymentStatus.WILL_BE_PAID
        and not due_date
    ):
        raise ValidationError(
            "A due date is required."
        )

    participant = Participant.objects.get(
        id=participant_id,
        is_active=True
    )

    order = WaterOrder.objects.create(
        participant=participant,
        order_number=f"ORD-{uuid.uuid4().hex[:10].upper()}",
        distributed_at=timezone.now(),
        notes=notes
    )

    for sequence_number in range(1, quantity + 1):
        gallon = Gallon.objects.create(
            order=order,
            sequence_number=sequence_number,
            color=gallon_color,
            unit_price=unit_price,
            payment_status=payment_status,
            due_date=due_date,
            paid_at=(
                timezone.now()
                if payment_status == Gallon.PaymentStatus.PAID
                else None
            )
        )

        PaymentStatusHistory.objects.create(
            gallon=gallon,
            old_status="",
            new_status=payment_status,
            note="Initial payment status"
        )

    return order

@transaction.atomic
def update_gallon_status(
    gallon_id,
    new_status,
    due_date=None,
    note="",
    changed_by=None
):
    valid_statuses = {
        choice[0]
        for choice in Gallon.PaymentStatus.choices
    }

    if new_status not in valid_statuses:
        raise ValidationError(
            "Invalid payment status."
        )

    if (
        new_status == Gallon.PaymentStatus.WILL_BE_PAID
        and not due_date
    ):
        raise ValidationError(
            "A due date is required."
        )

    gallon = Gallon.objects.select_for_update().get(
        id=gallon_id
    )

    old_status = gallon.payment_status

    if old_status == new_status:
        return gallon

    gallon.payment_status = new_status

    if new_status == Gallon.PaymentStatus.PAID:
        gallon.paid_at = timezone.now()
        gallon.due_date = None
    elif new_status == Gallon.PaymentStatus.WILL_BE_PAID:
        gallon.paid_at = None
        gallon.due_date = due_date
    else:
        gallon.paid_at = None
        gallon.due_date = None

    gallon.save()

    PaymentStatusHistory.objects.create(
        gallon=gallon,
        old_status=old_status,
        new_status=new_status,
        note=note,
        changed_by=changed_by
    )

    return gallon
