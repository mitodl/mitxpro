"""
Voucher forms tests
"""
from unittest.mock import patch

import pytest
from django.core.exceptions import ValidationError

from voucher.forms import UploadVoucherForm


@patch("voucher.forms.read_pdf", return_value="Success")
def test_clean_voucher(mock_pdf_parser, upload_voucher_form_with_file_field):
    """
    Test clean_voucher runs read_pdf on the given data
    """
    assert (
        UploadVoucherForm.clean_voucher(upload_voucher_form_with_file_field)
        == "Success"
    )
    mock_pdf_parser.assert_called_once_with(
        upload_voucher_form_with_file_field.cleaned_data["voucher"]
    )


@patch("voucher.forms.read_pdf", return_value=None)
def test_clean_voucher_error(mock_pdf_parser, upload_voucher_form_with_file_field):
    """
    Test clean_voucher raises a validation error on failed parse
    """
    with pytest.raises(ValidationError):
        UploadVoucherForm.clean_voucher(upload_voucher_form_with_file_field)
    mock_pdf_parser.assert_called_once_with(
        upload_voucher_form_with_file_field.cleaned_data["voucher"]
    )
