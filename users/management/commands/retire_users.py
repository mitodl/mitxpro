"""
Retire user(s) from MIT xPRO
"""
from argparse import RawTextHelpFormatter

from django.contrib.auth import get_user_model
from django.core.management import BaseCommand

from social_django.models import UserSocialAuth

from user_util import user_util

User = get_user_model()

RETIRED_USER_SALTS = ["mitxpro-retired-email"]
RETIRED_EMAIL_FMT = "retired_email_{}@retired.mit.edu"


class Command(BaseCommand):
    """
    Retire user from MIT xPRO
    """

    help = """
    Retire one or multiple users. For single user use:\n
    `./manage.py retire_users --user=foo` or do \n
    `./manage.py retire_users -u foo` \n
    
    For multiple users, add arg `--user` for each user i.e:\n
    `./manage.py retire_users --user=foo --user=bar --user=baz` or do \n
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
            help="Single or multiple username(s)",
        ),

    def get_retired_email(self, email):
        """ Convert user email to retired email format. """
        return user_util.get_retired_email(email, RETIRED_USER_SALTS, RETIRED_EMAIL_FMT)

    def handle(self, *args, **kwargs):
        usernames = kwargs.get("users", [])

        if not usernames:
            self.stderr.write(
                self.style.ERROR(
                    "No username(s) provided. Please provide username(s) using -u or --user."
                )
            )
            exit(1)

        for username in usernames:
            self.stdout.write("Retiring user: {username}".format(username=username))

            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(
                        "User: '{username}' does not exist in MIT xPRO".format(
                            username=username
                        )
                    )
                )
                continue

            if not user.is_active:
                self.stdout.write(
                    self.style.ERROR(
                        "User: '{username}' is already deactivated in MIT xPRO".format(
                            username=username
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
            UserSocialAuth.objects.filter(user=user).delete()

            self.stdout.write(
                "For  user: '{username}' SocialAuth rows deleted".format(
                    username=username
                )
            )

            self.stdout.write(
                self.style.SUCCESS(
                    "User: '{username}' is retired from MIT xPRO".format(
                        username=username
                    )
                )
            )
