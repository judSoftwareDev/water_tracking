from django.core.exceptions import ValidationError
from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Gallon, Participant, PaymentStatusHistory, WaterOrder
from .services import create_mixed_water_order, create_water_order


class CreateWaterOrderTests(TestCase):
    def setUp(self):
        self.participant = Participant.objects.create(
            participant_number="P-001",
            full_name="Test Buyer"
        )

    def test_creates_blue_gallons_for_assigned_buyer(self):
        order = create_water_order(
            participant_id=self.participant.id,
            quantity=2,
            unit_price=50,
            gallon_color=Gallon.GallonColor.BLUE
        )

        self.assertEqual(order.participant, self.participant)
        self.assertEqual(order.gallons.count(), 2)
        self.assertFalse(
            order.gallons.exclude(
                color=Gallon.GallonColor.BLUE
            ).exists()
        )

    def test_creates_pink_gallon(self):
        order = create_water_order(
            participant_id=self.participant.id,
            quantity=1,
            unit_price=55,
            gallon_color=Gallon.GallonColor.PINK
        )

        self.assertEqual(
            order.gallons.get().color,
            Gallon.GallonColor.PINK
        )

    def test_rejects_unknown_gallon_color(self):
        with self.assertRaises(ValidationError):
            create_water_order(
                participant_id=self.participant.id,
                quantity=1,
                unit_price=50,
                gallon_color="GREEN"
            )

    def test_creates_blue_and_pink_gallons_in_one_purchase(self):
        order = create_mixed_water_order(
            participant=self.participant,
            purchase_date=timezone.localdate(),
            blue_quantity=2,
            blue_unit_price=50,
            pink_quantity=1,
            pink_unit_price=55
        )

        self.assertEqual(order.gallons.count(), 3)
        self.assertEqual(
            order.gallons.filter(
                color=Gallon.GallonColor.BLUE
            ).count(),
            2
        )
        self.assertEqual(
            order.gallons.filter(
                color=Gallon.GallonColor.PINK
            ).count(),
            1
        )
        self.assertEqual(order.blue_gallon_count, 2)
        self.assertEqual(order.pink_gallon_count, 1)
        self.assertEqual(order.total_price, Decimal("155.00"))


class UserInterfaceTests(TestCase):
    def setUp(self):
        self.participant = Participant.objects.create(
            participant_number="P-002",
            full_name="Interface Buyer"
        )

    def test_main_pages_load(self):
        urls = (
            reverse("water:dashboard"),
            reverse("water:participant_list"),
            reverse("water:participant_detail", args=[self.participant.pk]),
            reverse("water:participant_create"),
            reverse("water:purchase_list"),
            reverse("water:purchase_create"),
        )

        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)

    def test_purchase_form_creates_mixed_purchase(self):
        response = self.client.post(
            reverse("water:purchase_create"),
            {
                "participant": self.participant.pk,
                "purchase_date": timezone.localdate().isoformat(),
                "blue_quantity": 1,
                "blue_unit_price": "50.00",
                "pink_quantity": 1,
                "pink_unit_price": "55.00",
                "payment_status": Gallon.PaymentStatus.NOT_PAID,
                "due_date": "",
                "notes": "Test purchase",
            }
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Gallon.objects.count(), 2)

        order = WaterOrder.objects.prefetch_related("gallons").get()
        self.assertEqual(order.total_price, Decimal("105.00"))

        list_response = self.client.get(reverse("water:purchase_list"))
        self.assertContains(list_response, "1 blue · 1 pink")
        self.assertContains(list_response, "₱105.00")

        detail_response = self.client.get(
            reverse("water:purchase_detail", args=[order.pk])
        )
        self.assertContains(detail_response, "Blue gallons")
        self.assertContains(detail_response, "Pink gallons")
        self.assertContains(detail_response, "Total price")
        self.assertContains(detail_response, "₱105.00")

    def test_delete_confirmation_does_not_delete_on_get(self):
        order = create_mixed_water_order(
            participant=self.participant,
            purchase_date=timezone.localdate(),
            blue_quantity=1,
            blue_unit_price=50,
            pink_quantity=0,
            pink_unit_price=0
        )

        response = self.client.get(
            reverse("water:purchase_delete", args=[order.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(WaterOrder.objects.filter(pk=order.pk).exists())

    def test_delete_purchase_cascades_to_gallons_and_history(self):
        order = create_mixed_water_order(
            participant=self.participant,
            purchase_date=timezone.localdate(),
            blue_quantity=1,
            blue_unit_price=50,
            pink_quantity=1,
            pink_unit_price=55
        )

        response = self.client.post(
            reverse("water:purchase_delete", args=[order.pk])
        )

        self.assertRedirects(response, reverse("water:purchase_list"))
        self.assertFalse(WaterOrder.objects.filter(pk=order.pk).exists())
        self.assertEqual(Gallon.objects.count(), 0)
        self.assertEqual(PaymentStatusHistory.objects.count(), 0)

# Create your tests here.
