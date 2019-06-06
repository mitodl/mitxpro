"""
Management command to sync all Users, Orders, Products, and Lines with Hubspot
and Line Items
"""
from django.core.management import BaseCommand
from requests import HTTPError

from ecommerce.models import Product, Order, Line
from hubspot.api import (
    make_contact_sync_message,
    make_product_sync_message,
    make_deal_sync_message,
    make_line_item_sync_message,
    send_hubspot_request,
)
from hubspot.tasks import HUBSPOT_SYNC_URL
from users.models import User


class Command(BaseCommand):
    """
    Command to sync all Users, Orders, Products, and Lines with Hubspot
    """

    help = (
        "Sync all Users, Orders, Products, and Lines with Hubspot. Hubspot API key must be set and Hubspot settings"
        "must be configured with configure_hubspot_settings"
    )

    @staticmethod
    def bulk_sync_model(model, make_object_sync_message, object_type):
        """
        Sync all database objects of a certain type with hubspot
        Args:
            model (Class) class to sync with hubspot
            make_object_sync_message (function) function that takes an objectID and
                returns a sync message for that model
            object_type (str) one of "CONTACT", "DEAL", "PRODUCT", "LINE_ITEM"
        """
        sync_messages = [
            make_object_sync_message(obj.id) for obj in model.objects.all()
        ]
        while len(sync_messages) > 0:
            staged_messages = sync_messages[0:200]
            sync_messages = sync_messages[200:]

            print("    Sending sync message...")
            try:
                response = send_hubspot_request(
                    object_type, HUBSPOT_SYNC_URL, "PUT", body=staged_messages
                )
                response.raise_for_status()
            except HTTPError as error:
                print(
                    f"    Sync message failed with status {error.request.status_code}"
                )

    def sync_contacts(self):
        """
        Sync all users with contacts in hubspot
        """
        print("  Syncing users with hubspot contacts...")
        self.bulk_sync_model(User, make_contact_sync_message, "CONTACT")
        print("  Finished")

    def sync_products(self):
        """
        Sync all products with products in hubspot
        """
        print("  Syncing products with hubspot products...")
        self.bulk_sync_model(Product, make_product_sync_message, "PRODUCT")
        print("  Finished")

    def sync_deals(self):
        """
        Sync all orders with deals in hubspot
        """
        print("  Syncing orders with hubspot deals...")
        self.bulk_sync_model(Order, make_deal_sync_message, "DEAL")
        print("  Finished")

    def sync_line_items(self):
        """
        Sync all lines with line_items in hubspot
        """
        print("  Syncing lines with hubspot line items...")
        self.bulk_sync_model(Line, make_line_item_sync_message, "LINE_ITEM")
        print("  Finished")

    def sync_all(self):
        """
        Sync all Users, Orders, Products, and Lines with Hubspot.
        """
        self.sync_contacts()
        self.sync_products()
        self.sync_deals()
        self.sync_line_items()

    def add_arguments(self, parser):
        """
        Definition of arguments this command accepts
        """
        parser.add_argument(
            "--contacts",
            "--users",
            dest="sync_contacts",
            action="store_true",
            help="Sync all users",
        )
        parser.add_argument(
            "--products",
            dest="sync_products",
            action="store_true",
            help="Sync all products",
        )
        parser.add_argument(
            "--deals",
            "--orders",
            dest="sync_deals",
            action="store_true",
            help="Sync all orders",
        )
        parser.add_argument(
            "--lines",
            "--line-items",
            dest="sync_line_items",
            action="store_true",
            help="Sync all lines",
        )

    def handle(self, *args, **options):
        print("Syncing with hubspot...")
        if not (
            options["sync_contacts"]
            or options["sync_products"]
            or options["sync_deals"]
            or options["sync_line_items"]
        ):
            # If no flags are set, sync everything
            self.sync_all()
        else:
            # If some flags are set, sync the specified models
            if options["sync_contacts"]:
                self.sync_contacts()
            if options["sync_products"]:
                self.sync_products()
            if options["sync_deals"]:
                self.sync_deals()
            if options["sync_line_items"]:
                self.sync_line_items()

        print("Hubspot sync complete")
