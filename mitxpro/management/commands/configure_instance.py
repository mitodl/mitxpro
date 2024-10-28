"""
Meta-command to help set up a freshly configured MITxPro instance.

Running this will perform the following functions:
- Configures a superuser account
- Creates the OAuth2 application record for edX (optionally with an existing
  client ID and secret)
- Create seed data and configure wagtail by using seed_data management command

If the --tutor/-T option is passed, the command will use the local.edly.io
address for links to edX rather than edx.odl.local:18000.

This uses other management commands to complete these tasks. So, if you just
want to run part of this, use one of these commands:
- createsuperuser to create the super user
- seed_data to configure wagtail and create seed/dummy courses and programs

There are some steps that this command won't do for you:
- Completing the integration between MITxPro and devstack - there are still
  steps that you need to take to finish that process

"""

from django.core.management import BaseCommand, call_command
from oauth2_provider.models import Application


class Command(BaseCommand):
    """
    Bootstraps a fresh MITxPro instance.
    """

    def add_arguments(self, parser):
        """Parses command line arguments."""

        parser.add_argument(
            "platform",
            help="Your platform (none, macos, or linux; defaults to none). None skips OAuth2 record creation.",
            type=str,
            choices=["none", "macos", "linux"],
            nargs="?",
            const="none",
        )

        parser.add_argument(
            "--dont-create-superuser",
            "-S",
            help="Don't create a superuser account.",
            action="store_false",
            dest="superuser",
        )

        parser.add_argument(
            "--edx-oauth-client",
            help="Use the provided OAuth2 client ID, rather than making a new one.",
            type=str,
            nargs="?",
        )

        parser.add_argument(
            "--edx-oauth-secret",
            help="Use the provided OAuth2 client secret, rather than making a new one.",
            type=str,
            nargs="?",
        )

        parser.add_argument(
            "--gateway",
            help="Specify the gateway IP. (Required for Linux users.)",
            type=str,
            nargs="?",
        )

        parser.add_argument(
            "--tutor",
            "-T",
            help="Configure for Tutor.",
            action="store_true",
            dest="tutor",
        )

        parser.add_argument(
            "--tutor-dev",
            help="Configure for Tutor Dev/Nightly.",
            action="store_true",
            dest="tutordev",
        )

    def determine_edx_hostport(self, *args, **kwargs):  # noqa: ARG002
        """Returns a tuple of the edX host and port depending on what the user's passed in"""

        if kwargs["tutor"]:
            return ("local.edly.io", "")
        elif kwargs["tutordev"]:
            return ("local.edly.io:8000", ":8000")
        else:
            return ("edx.odl.local:18000", ":18000")

    def handle(self, *args, **kwargs):  # noqa: ARG002
        """Coordinates the other commands."""

        (edx_host, edx_gateway_port) = self.determine_edx_hostport(**kwargs)

        # Step 1: run createsuperuesr
        if kwargs["superuser"]:
            self.stdout.write(self.style.SUCCESS("Creating superuser..."))

            call_command("createsuperuser")

        # Step 2: create OAuth2 provider records
        oauth2_app = None
        if kwargs["platform"] != "none":
            self.stdout.write(self.style.SUCCESS("Creating OAuth2 app..."))

            if kwargs["platform"] == "macos":
                redirects = "\n".join(
                    [
                        f"http://{edx_host}/auth/complete/mitxpro-oauth2/",
                        f"http://host.docker.internal{edx_gateway_port}/auth/complete/mitxpro-oauth2/",
                    ]
                )
            else:
                if kwargs["gateway"] is None:
                    self.stdout.write(
                        self.style.ERROR(
                            f"Gateway required for platform type {kwargs['platform']}."
                        )
                    )
                    exit(-1)  # noqa: PLR1722

                redirects = "\n".join(
                    [
                        f"http://{edx_host}/auth/complete/mitxpro-oauth2/",
                        f"http://{kwargs['gateway']}{edx_gateway_port}/auth/complete/mitxpro-oauth2/",
                    ]
                )

            (oauth2_app, _) = Application.objects.get_or_create(
                name="edx-oauth-app",
                defaults={
                    "client_type": "confidential",
                    "authorization_grant_type": "authorization-code",
                    "skip_authorization": True,
                    "redirect_uris": redirects,
                },
            )

            if kwargs["edx_oauth_client"] is not None:
                oauth2_app.client_id = kwargs["edx_oauth_client"]

            if kwargs["edx_oauth_secret"] is not None:
                oauth2_app.client_secret = kwargs["edx_oauth_secret"]

            oauth2_app.save()

            self.stdout.write(
                self.style.SUCCESS(
                    f"Created OAuth2 app {oauth2_app.name} for edX. Your client ID is \n{oauth2_app.client_id}\nand your secret is\n{oauth2_app.client_secret}\n\n"
                )
            )

        # Step 3: create example course(s) and program(s)
        self.stdout.write(self.style.SUCCESS("Creating Seed Data..."))
        call_command("seed_data")
        self.stdout.write(self.style.SUCCESS("Seed Data Created"))

        # Print OAuth2 app details at the end of the file for user convenience
        # This allows the user to access their client ID and secret without needing to scroll up,
        # making it easily accessible after the script completes execution.
        if oauth2_app:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Created OAuth2 app {oauth2_app.name} for edX. Your client ID is \n{oauth2_app.client_id}\nand your secret is\n{oauth2_app.client_secret}\n\n"
                )
            )

        self.stdout.write(self.style.SUCCESS("Done!"))
