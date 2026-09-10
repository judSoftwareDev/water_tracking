from django.conf import settings
from django.db import models


class Participant(models.Model):
    participant_number = models.CharField(
        max_length=30,
        unique=True
    )
    full_name = models.CharField(max_length=150)
    phone = models.CharField(
        max_length=30,
        blank=True
    )
    address = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return self.full_name


class WaterOrder(models.Model):
    participant = models.ForeignKey(
        Participant,
        on_delete=models.PROTECT,
        related_name="orders",
        verbose_name="assigned buyer"
    )
    order_number = models.CharField(
        max_length=30,
        unique=True
    )
    distributed_at = models.DateTimeField(
        verbose_name="purchase date"
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"{self.order_number} - {self.participant.full_name}"

    class Meta:
        verbose_name = "gallon purchase"
        verbose_name_plural = "gallon purchases"


class Gallon(models.Model):
    class GallonColor(models.TextChoices):
        BLUE = "BLUE", "Blue"
        PINK = "PINK", "Pink"

    class PaymentStatus(models.TextChoices):
        PAID = "PAID", "Paid"
        NOT_PAID = "NOT_PAID", "Not Paid"
        WILL_BE_PAID = "WILL_BE_PAID", "Will Be Paid"

    order = models.ForeignKey(
        WaterOrder,
        on_delete=models.CASCADE,
        related_name="gallons"
    )
    sequence_number = models.PositiveIntegerField()
    color = models.CharField(
        max_length=10,
        choices=GallonColor.choices,
        default=GallonColor.BLUE
    )
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )
    payment_status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.NOT_PAID
    )
    due_date = models.DateField(
        null=True,
        blank=True
    )
    paid_at = models.DateTimeField(
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["order", "sequence_number"],
                name="unique_gallon_per_order"
            )
        ]

    def __str__(self):
        return (
            f"{self.order.order_number} - "
            f"{self.get_color_display()} gallon "
            f"{self.sequence_number}"
        )


class PaymentStatusHistory(models.Model):
    gallon = models.ForeignKey(
        Gallon,
        on_delete=models.CASCADE,
        related_name="status_history"
    )
    old_status = models.CharField(
        max_length=20,
        choices=Gallon.PaymentStatus.choices,
        blank=True
    )
    new_status = models.CharField(
        max_length=20,
        choices=Gallon.PaymentStatus.choices
    )
    note = models.TextField(blank=True)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    changed_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["-changed_at"]
