from django.contrib import messages
from django.db.models import Count, DecimalField, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, redirect, render

from .forms import GallonStatusForm, ParticipantForm, PurchaseForm
from .models import Gallon, Participant, WaterOrder
from .services import create_mixed_water_order, update_gallon_status


MONEY_FIELD = DecimalField(max_digits=12, decimal_places=2)


def dashboard(request):
    gallons = Gallon.objects.all()
    totals = gallons.aggregate(
        total=Count("id"),
        paid=Count("id", filter=Q(payment_status=Gallon.PaymentStatus.PAID)),
        not_paid=Count(
            "id",
            filter=Q(payment_status=Gallon.PaymentStatus.NOT_PAID)
        ),
        will_be_paid=Count(
            "id",
            filter=Q(payment_status=Gallon.PaymentStatus.WILL_BE_PAID)
        ),
        outstanding=Coalesce(
            Sum(
                "unit_price",
                filter=~Q(payment_status=Gallon.PaymentStatus.PAID)
            ),
            Value(0),
            output_field=MONEY_FIELD
        )
    )
    color_totals = gallons.values("color").annotate(total=Count("id"))
    colors = {item["color"]: item["total"] for item in color_totals}
    recent_orders = WaterOrder.objects.select_related(
        "participant"
    ).prefetch_related("gallons").order_by("-distributed_at")[:6]

    return render(request, "water/dashboard.html", {
        "totals": totals,
        "blue_total": colors.get(Gallon.GallonColor.BLUE, 0),
        "pink_total": colors.get(Gallon.GallonColor.PINK, 0),
        "recent_orders": recent_orders,
    })


def participant_list(request):
    query = request.GET.get("q", "").strip()
    participants = Participant.objects.annotate(
        gallon_total=Count("orders__gallons"),
        paid_total=Count(
            "orders__gallons",
            filter=Q(
                orders__gallons__payment_status=Gallon.PaymentStatus.PAID
            )
        ),
        outstanding_total=Count(
            "orders__gallons",
            filter=~Q(
                orders__gallons__payment_status=Gallon.PaymentStatus.PAID
            )
        ),
    ).order_by("full_name")

    if query:
        participants = participants.filter(
            Q(full_name__icontains=query)
            | Q(participant_number__icontains=query)
        )

    return render(request, "water/participant_list.html", {
        "participants": participants,
        "query": query,
    })


def participant_create(request):
    form = ParticipantForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        participant = form.save()
        messages.success(request, "Participant added successfully.")
        return redirect("water:participant_detail", pk=participant.pk)

    return render(request, "water/form_page.html", {
        "form": form,
        "title": "Add participant",
        "subtitle": "Create a record for a person assigned to buy gallons.",
        "submit_label": "Save participant",
    })


def participant_edit(request, pk):
    participant = get_object_or_404(Participant, pk=pk)
    form = ParticipantForm(request.POST or None, instance=participant)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Participant updated successfully.")
        return redirect("water:participant_detail", pk=participant.pk)

    return render(request, "water/form_page.html", {
        "form": form,
        "title": "Edit participant",
        "subtitle": participant.full_name,
        "submit_label": "Save changes",
    })


def participant_detail(request, pk):
    participant = get_object_or_404(Participant, pk=pk)
    gallons = Gallon.objects.filter(
        order__participant=participant
    )
    totals = gallons.aggregate(
        total=Count("id"),
        paid=Count("id", filter=Q(payment_status=Gallon.PaymentStatus.PAID)),
        not_paid=Count(
            "id",
            filter=Q(payment_status=Gallon.PaymentStatus.NOT_PAID)
        ),
        will_be_paid=Count(
            "id",
            filter=Q(payment_status=Gallon.PaymentStatus.WILL_BE_PAID)
        ),
        outstanding=Coalesce(
            Sum(
                "unit_price",
                filter=~Q(payment_status=Gallon.PaymentStatus.PAID)
            ),
            Value(0),
            output_field=MONEY_FIELD
        )
    )
    orders = participant.orders.prefetch_related("gallons").order_by(
        "-distributed_at"
    )

    return render(request, "water/participant_detail.html", {
        "participant": participant,
        "totals": totals,
        "orders": orders,
    })


def purchase_list(request):
    orders = WaterOrder.objects.select_related(
        "participant"
    ).prefetch_related("gallons").order_by("-distributed_at")
    return render(request, "water/purchase_list.html", {"orders": orders})


def purchase_create(request):
    form = PurchaseForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        order = create_mixed_water_order(**form.cleaned_data)
        messages.success(request, "Gallon purchase recorded successfully.")
        return redirect("water:purchase_detail", pk=order.pk)

    return render(request, "water/purchase_form.html", {"form": form})


def purchase_detail(request, pk):
    order = get_object_or_404(
        WaterOrder.objects.select_related("participant").prefetch_related(
            "gallons"
        ),
        pk=pk
    )
    return render(request, "water/purchase_detail.html", {"order": order})


def purchase_delete(request, pk):
    order = get_object_or_404(
        WaterOrder.objects.select_related("participant").prefetch_related(
            "gallons"
        ),
        pk=pk
    )

    if request.method == "POST":
        order_number = order.order_number
        order.delete()
        messages.success(
            request,
            f"Purchase {order_number} was deleted successfully."
        )
        return redirect("water:purchase_list")

    return render(request, "water/purchase_confirm_delete.html", {
        "order": order,
    })


def gallon_status_update(request, pk):
    gallon = get_object_or_404(
        Gallon.objects.select_related("order", "order__participant"),
        pk=pk
    )
    initial = {
        "payment_status": gallon.payment_status,
        "due_date": gallon.due_date,
    }
    form = GallonStatusForm(request.POST or None, initial=initial)

    if request.method == "POST" and form.is_valid():
        update_gallon_status(
            gallon_id=gallon.id,
            new_status=form.cleaned_data["payment_status"],
            due_date=form.cleaned_data["due_date"],
            note=form.cleaned_data["note"],
            changed_by=(request.user if request.user.is_authenticated else None)
        )
        messages.success(request, "Payment status updated.")
        return redirect("water:purchase_detail", pk=gallon.order_id)

    return render(request, "water/gallon_status_form.html", {
        "form": form,
        "gallon": gallon,
    })

# Create your views here.
