"""
block user(s) from MIT xPRO
"""

import sys
from argparse import RawTextHelpFormatter

from django.core.management import BaseCommand

from authentication.utils import block_user_email
from mail.api import validate_email_addresses
from mail.exceptions import MultiEmailValidationError


class Command(BaseCommand):
    """
    block user(s) from MIT xPRO.
    """

    help = """
    Block one or multiple users. email will be used to identify a user.

    For single user use:\n
    `./manage.py block_users --user=foo@email.com` or do \n

    For multiple users, add arg `--user` for each user i.e:\n
    `./manage.py block_users --user=foo@email.com --user=bar@email.com --user=abc@email.com` or do \n
    """

    def create_parser(self, prog_name, subcommand):
        """
        Create parser to add new line in help text.
        """
        parser = super().create_parser(prog_name, subcommand)
        parser.formatter_class = RawTextHelpFormatter
        return parser

    def add_arguments(self, parser):
        """Parse arguments"""
        parser.add_argument(
            "-u",
            "--user",
            action="append",
            default=[],
            dest="users",
            help="Single or multiple username(s) or email(s)",
        )

    def handle(self, *args, **kwargs):  # noqa: ARG002
        users = kwargs.get("users", [])
        if not users:
            self.stderr.write(
                self.style.ERROR(
                    "No user(s) provided. Please provide user(s) using -u or --user."
                )
            )
            sys.exit(1)

        try:
            validate_email_addresses(users)
        except MultiEmailValidationError as exep:
            self.stdout.write(
                self.style.ERROR(
                    "The following provided emails ({emails})  are not in valid format."
                ).format(emails=exep.invalid_emails)
            )
            sys.exit(2)

        for user_email in users:
            msg = block_user_email(email=user_email)
            if msg:
                self.stdout.write(self.style.SUCCESS(msg))
