from django.contrib import admin

from .models import (
    Gallon,
    Participant,
    PaymentStatusHistory,
    WaterOrder,
)


class GallonInline(admin.TabularInline):
    model = Gallon
    extra = 0
    fields = (
        "sequence_number",
        "color",
        "unit_price",
        "payment_status",
        "due_date",
        "paid_at",
    )


@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = (
        "participant_number",
        "full_name",
        "phone",
        "is_active",
    )
    search_fields = (
        "participant_number",
        "full_name",
    )
    list_filter = ("is_active",)


@admin.register(WaterOrder)
class WaterOrderAdmin(admin.ModelAdmin):
    list_display = (
        "order_number",
        "participant",
        "distributed_at",
        "blue_gallons",
        "pink_gallons",
    )
    search_fields = (
        "order_number",
        "participant__full_name",
    )
    inlines = [GallonInline]

    @admin.display(description="Blue gallons")
    def blue_gallons(self, order):
        return order.gallons.filter(
            color=Gallon.GallonColor.BLUE
        ).count()

    @admin.display(description="Pink gallons")
    def pink_gallons(self, order):
        return order.gallons.filter(
            color=Gallon.GallonColor.PINK
        ).count()


@admin.register(Gallon)
class GallonAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "order",
        "sequence_number",
        "color",
        "unit_price",
        "payment_status",
        "due_date",
    )
    list_filter = ("color", "payment_status")
    search_fields = (
        "order__order_number",
        "order__participant__full_name",
    )


admin.site.register(PaymentStatusHistory)
