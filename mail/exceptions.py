"""Custom mail app exceptions"""


class MultiEmailValidationError(Exception):
    """
    General exception for failures while validating multiple emails
    """

    def __init__(self, invalid_emails, msg=None):
        """
        Args:
            invalid_emails (set of str): All email addresses that failed validation
            msg (str): A custom exception message
        """
        self.invalid_emails = invalid_emails
        super().__init__(msg)
