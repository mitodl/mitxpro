"""Sheets app exceptions"""


class SheetValidationException(Exception):
    """
    General exception for failures during the validation of Sheet data
    """


class SheetUpdateException(Exception):
    """
    General exception for failures while attempting to update a Sheet via API
    """
