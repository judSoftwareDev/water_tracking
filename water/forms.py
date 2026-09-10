from django import forms
from django.utils import timezone

from .models import Gallon, Participant


class DateInput(forms.DateInput):
    input_type = "date"


class ParticipantForm(forms.ModelForm):
    class Meta:
        model = Participant
        fields = (
            "participant_number",
            "full_name",
            "phone",
            "address",
            "is_active",
        )
        widgets = {
            "address": forms.Textarea(attrs={"rows": 3}),
        }


class PurchaseForm(forms.Form):
    participant = forms.ModelChoiceField(
        queryset=Participant.objects.none(),
        label="Assigned buyer"
    )
    purchase_date = forms.DateField(
        initial=timezone.localdate,
        widget=DateInput()
    )
    blue_quantity = forms.IntegerField(
        min_value=0,
        initial=0
    )
    blue_unit_price = forms.DecimalField(
        min_value=0,
        max_digits=10,
        decimal_places=2,
        initial=0
    )
    pink_quantity = forms.IntegerField(
        min_value=0,
        initial=0
    )
    pink_unit_price = forms.DecimalField(
        min_value=0,
        max_digits=10,
        decimal_places=2,
        initial=0
    )
    payment_status = forms.ChoiceField(
        choices=Gallon.PaymentStatus.choices,
        initial=Gallon.PaymentStatus.NOT_PAID
    )
    due_date = forms.DateField(
        required=False,
        widget=DateInput(),
        help_text="Required only when the status is Will Be Paid."
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 3})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["participant"].queryset = Participant.objects.filter(
            is_active=True
        ).order_by("full_name")

    def clean(self):
        cleaned_data = super().clean()
        blue_quantity = cleaned_data.get("blue_quantity") or 0
        pink_quantity = cleaned_data.get("pink_quantity") or 0
        status = cleaned_data.get("payment_status")

        if blue_quantity + pink_quantity < 1:
            raise forms.ValidationError(
                "Enter at least one blue or pink gallon."
            )

        if (
            status == Gallon.PaymentStatus.WILL_BE_PAID
            and not cleaned_data.get("due_date")
        ):
            self.add_error(
                "due_date",
                "A due date is required for Will Be Paid gallons."
            )

        return cleaned_data


class GallonStatusForm(forms.Form):
    payment_status = forms.ChoiceField(
        choices=Gallon.PaymentStatus.choices,
        label="New payment status"
    )
    due_date = forms.DateField(
        required=False,
        widget=DateInput()
    )
    note = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 2}),
        help_text="Optional explanation for the status change."
    )

    def clean(self):
        cleaned_data = super().clean()
        if (
            cleaned_data.get("payment_status")
            == Gallon.PaymentStatus.WILL_BE_PAID
            and not cleaned_data.get("due_date")
        ):
            self.add_error(
                "due_date",
                "A due date is required for Will Be Paid gallons."
            )
        return cleaned_data
