"""
Unblock user(s) from MIT xPRO
"""
import hashlib
from argparse import RawTextHelpFormatter
from urllib.parse import urlparse
import sys

from django.contrib.auth import get_user_model
from django.core.management import BaseCommand

from social_django.models import UserSocialAuth

from mail.api import validate_email_addresses
from mail.exceptions import MultiEmailValidationError
from users.api import fetch_users
from users.models import BlockList

from mitxpro import settings

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

    def create_parser(self, prog_name, subcommand):  # pylint: disable=arguments-differ
        """
        create parser to add new line in help text.
        """
        parser = super().create_parser(prog_name, subcommand)
        parser.formatter_class = RawTextHelpFormatter
        return parser

    def add_arguments(self, parser):
        """parse arguments"""

        # pylint: disable=expression-not-assigned
        parser.add_argument(
            "-u",
            "--user",
            action="append",
            default=[],
            dest="users",
            help="Single or multiple username(s) or email(s)",
        )

    def handle(self, *args, **kwargs):
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
        except MultiEmailValidationError:
            self.stdout.write(
                self.style.ERROR(
                    "One or more provided user email addresses {users} are not in valid format."
                ).format(users=users)
            )
            sys.exit(2)

        for user_email in users:
            hash_object = hashlib.md5(user_email.lower().encode("utf-8"))
            blocked_user = BlockList.objects.filter(
                hashed_email=hash_object.hexdigest()
            )
            if blocked_user:
                self.stdout.write(
                    self.style.SUCCESS(
                        "Email {email} has been removed from the blocklist of MIT xPRO.".format(
                            email=user_email
                        )
                    )
                )
                blocked_user.delete()
            else:
                self.stdout.write(
                    self.style.WARNING(
                        "Email {email} was not found in the blocklist.".format(
                            email=user_email
                        )
                    )
                )
