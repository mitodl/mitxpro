"""Fixtures relevant to the sheets app test suite"""

import pytest


@pytest.fixture(autouse=True)
def sheets_settings(settings):
    """Default settings for sheets tests"""
    settings.SHEETS_REQ_EMAIL_COL = 7
    settings.SHEETS_REQ_PROCESSED_COL = 8
    settings.SHEETS_REQ_ERROR_COL = 9
    settings.SHEETS_REQ_CALCULATED_COLUMNS = {
        settings.SHEETS_REQ_EMAIL_COL,
        settings.SHEETS_REQ_PROCESSED_COL,
        settings.SHEETS_REQ_ERROR_COL,
    }
    _uppercase_a_ord = ord("A")
    settings.SHEETS_REQ_PROCESSED_COL_LETTER = chr(
        settings.SHEETS_REQ_PROCESSED_COL + _uppercase_a_ord
    )
    settings.SHEETS_REQ_ERROR_COL_LETTER = chr(
        settings.SHEETS_REQ_ERROR_COL + _uppercase_a_ord
    )
    settings.SHEETS_ADMIN_EMAILS = ["admin@example.com"]
