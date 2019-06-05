"""
Voucher upload forms
"""
from django import forms
from django.core.exceptions import ValidationError

from voucher.utils import read_pdf


VOUCHER_PARSE_ERROR = "Failed to parse PDF"


class UploadVoucherForm(forms.Form):
    """
    UploadVoucherForm is a single field form for uploading a voucher and parsing it for cleaned data
    """

    voucher = forms.FileField()

    def clean_voucher(self):
        """Parse Voucher data and return"""
        parsed_data = read_pdf(self.cleaned_data["voucher"])
        if parsed_data is None:
            raise ValidationError(VOUCHER_PARSE_ERROR)
        return parsed_data
