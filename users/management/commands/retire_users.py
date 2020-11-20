"""
Retire user(s) from MIT xPRO
"""
from argparse import RawTextHelpFormatter
from urllib.parse import urlparse
import sys

from django.contrib.auth import get_user_model
from django.core.management import BaseCommand

from social_django.models import UserSocialAuth

from user_util import user_util
from users.api import fetch_users

from mitxpro import settings

User = get_user_model()

RETIRED_USER_SALTS = ["mitxpro-retired-email"]
RETIRED_EMAIL_FMT = "retired_email_{}@retired." + "{}".format(
    urlparse(settings.SITE_BASE_URL).netloc
)


class Command(BaseCommand):
    """
    Retire user from MIT xPRO
    """

    help = """
    Retire one or multiple users. Username or email can be used to identify a user.

    For single user use:\n
    `./manage.py retire_users --user=foo` or do \n
    `./manage.py retire_users -u foo` \n or do \n
    `./manage.py retire_users -u foo@email.com` \n or do \n

    For multiple users, add arg `--user` for each user i.e:\n
    `./manage.py retire_users --user=foo --user=bar --user=baz` or do \n
    `./manage.py retire_users --user=foo@email.com --user=bar@email.com --user=baz` or do \n
    `./manage.py retire_users -u foo -u bar -u baz`
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

    def get_retired_email(self, email):
        """ Convert user email to retired email format. """
        return user_util.get_retired_email(email, RETIRED_USER_SALTS, RETIRED_EMAIL_FMT)

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
            self.stdout.write("Retiring user: {user}".format(user=user))
            if not user.is_active:
                self.stdout.write(
                    self.style.ERROR(
                        "User: '{user}' is already deactivated in MIT xPRO".format(
                            user=user
                        )
                    )
                )
                continue

            user.is_active = False

            # Change user password & email
            email = user.email
            user.email = self.get_retired_email(user.email)
            user.set_unusable_password()
            user.save()

            self.stdout.write(
                "Email changed from {email} to {retired_email} and password is not useable now".format(
                    email=email, retired_email=user.email
                )
            )

            # reset user social auth
            auth_deleted_count = UserSocialAuth.objects.filter(user=user).delete()

            if auth_deleted_count:
                self.stdout.write(
                    "For  user: '{user}' SocialAuth rows deleted".format(user=user)
                )

            self.stdout.write(
                self.style.SUCCESS(
                    "User: '{user}' is retired from MIT xPRO".format(user=user)
                )
            )
