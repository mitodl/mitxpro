"""
Management command to decrypts a user's ExportInquiryLog record
"""
import sys

from django.core.management import BaseCommand
from django.contrib.auth import get_user_model
from nacl.encoding import Base64Encoder
from nacl.public import PrivateKey

from compliance.api import decrypt_exports_inquiry, get_latest_exports_inquiry

User = get_user_model()


class Command(BaseCommand):
    """
    Management command to decrypts a user's ExportInquiryLog record
    """

    help = "Decrypts a user's ExportInquiryLog record"

    def add_arguments(self, parser):
        """
        Definition of arguments this command accepts
        """
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument("--user-id", help="the id of the user")
        group.add_argument("--email", help="the email of the user")
        group.add_argument("--username", help="the username of the user")

    def handle(self, *args, **options):
        """Run the command"""

        if options["user_id"]:
            user = User.objects.get(id=options["user_id"])
        elif options["username"]:
            user = User.objects.get(username=options["username"])
        elif options["email"]:
            user = User.objects.get(email=options["email"])

        if user is None:
            self.stderr.write(self.style.ERROR("User doesn't exist "))
            sys.exit(1)

        log = get_latest_exports_inquiry(user)

        if log is None:
            self.stderr.write(self.style.ERROR("User has no ExportsInquiryLog records"))
            sys.exit(2)

        encoded_private_key = input("NaCL Private Key (Base64-encoded): ")

        private_key = PrivateKey(encoded_private_key, encoder=Base64Encoder)

        decrypted = decrypt_exports_inquiry(log, private_key)

        self.stdout.write(self.style.SUCCESS("Request:"))
        self.stdout.write(
            self.style.SUCCESS("------------------------------------------------------")
        )
        self.stdout.write(self.style.SUCCESS(decrypted.request.decode("utf-8")))
        self.stdout.write(
            self.style.SUCCESS("------------------------------------------------------")
        )

        self.stdout.write(self.style.SUCCESS(""))

        self.stdout.write(self.style.SUCCESS("Response:"))
        self.stdout.write(
            self.style.SUCCESS("------------------------------------------------------")
        )
        self.stdout.write(self.style.SUCCESS(decrypted.response.decode("utf-8")))
        self.stdout.write(
            self.style.SUCCESS("------------------------------------------------------")
        )
