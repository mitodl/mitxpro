"""
block user(s) from MIT xPRO
"""
import hashlib
from argparse import RawTextHelpFormatter
from urllib.parse import urlparse
import sys

from django.contrib.auth import get_user_model
from django.core.management import BaseCommand

from social_django.models import UserSocialAuth
from authentication.utils import block_user_email
from mail.api import validate_email_addresses
from mail.exceptions import MultiEmailValidationError
from users.api import fetch_users
from users.models import BlockList

from mitxpro import settings

User = get_user_model()


class Command(BaseCommand):
    """
    block user(s) from MIT xPRO.
    """

    help = """
    Block one or multiple users. email will be used to identify a user.

    For single user use:\n
    `./manage.py block_users --user=foo@email.com` or do \n
    `./manage.py block_users -u foo@email.com` \n or do \n
    `./manage.py block_users --user=foo` or do \n
    `./manage.py block_users -u foo` \n or do \n
    
    For multiple users, add arg `--user` for each user i.e:\n
    `./manage.py block_users --user=foo --user=bar --user=baz` or do \n
    `./manage.py block_users --user=foo@email.com --user=bar@email.com --user=abc@email.com` or do \n
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

        users = fetch_users(kwargs["users"])
        for user in users:
            email = user.email
            msg = block_user_email(email=email)
            if msg:
                self.stdout.write(self.style.SUCCESS(msg))
