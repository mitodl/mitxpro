"""Sheets app exceptions"""


class SheetValidationException(Exception):
    """
    General exception for failures during the validation of Sheet data
    """


class SheetUpdateException(Exception):
    """
    General exception for failures while attempting to update a Sheet via API
    """


class SheetOutOfSyncException(Exception):
    """
    General exception for situations where the data in a spreadsheet does not reflect the state of the database
    """

    def __init__(self, coupon_gen_request, row_index, msg=None):
        self.coupon_gen_request = coupon_gen_request
        self.row_index = row_index
        super().__init__(msg)


class InvalidSheetProductException(Exception):
    """
    Exception for an invalid product entered into the coupon request spreadsheet
    """
