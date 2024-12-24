"""
Unblock user(s) from MIT xPRO
"""

import sys
from argparse import RawTextHelpFormatter

from django.contrib.auth import get_user_model
from django.core.management import BaseCommand

from authentication.utils import get_md5_hash
from mail.api import validate_email_addresses
from mail.exceptions import MultiEmailValidationError
from users.models import BlockList

User = get_user_model()


class Command(BaseCommand):
    """
    Unblock user(s) from MIT xPRO.
    """

    help = """
    Unblick one or multiple users. email will be used to identify a user.

    For single user use:\n
    `./manage.py unblock_users --user=foo@email.com` or do \n
    `./manage.py unblock_users -u foo@email.com` \n or do \n

    For multiple users, add arg `--user` for each user i.e:\n
    `./manage.py unblock_users --user=foo@email.com --user=bar@email.com --user=abc@email.com` or do \n
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
            help="Single or multiple email(s)",
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
            hash_object = get_md5_hash(user_email)
            blocked_user = BlockList.objects.filter(
                hashed_email=hash_object.hexdigest()
            )
            if blocked_user:
                blocked_user.delete()
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Email {user_email} has been removed from the blocklist of MIT xPRO."
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        "Email {email} was not found in the blocklist.".format(  # noqa: UP032
                            email=user_email
                        )
                    )
                )
