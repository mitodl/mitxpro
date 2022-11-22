"""
Management command to sync all Users, Orders, Products, and Lines with Hubspot
and Line Items
"""
from django.core.management import BaseCommand
from requests import HTTPError
from b2b_ecommerce.models import B2BOrder
from ecommerce.models import Product, Order, Line
from hubspot.api import (
    make_contact_sync_message,
    make_product_sync_message,
    make_deal_sync_message,
    make_b2b_deal_sync_message,
    make_b2b_product_sync_message,
    make_b2b_contact_sync_message,
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
    def bulk_sync_model(
        objects, make_object_sync_message, object_type, use_email=False
    ):
        """
        Sync all database objects of a certain type with hubspot
        Args:
            objects (iterable) objects to sync
            make_object_sync_message (function) function that takes an objectID and
                returns a sync message for that model
            object_type (str) one of "CONTACT", "DEAL", "PRODUCT", "LINE_ITEM"
            use_email (bool) either we need to pass the object ID or Email in case of "USER" queryset.
        """
        if objects.model is B2BOrder and use_email:
            sync_messages = [make_object_sync_message(obj.email)[0] for obj in objects]
        else:
            sync_messages = [make_object_sync_message(obj.id)[0] for obj in objects]
        while len(sync_messages) > 0:
            staged_messages = sync_messages[0:200]
            sync_messages = sync_messages[200:]

            print("    Sending sync message...")
            response = send_hubspot_request(
                object_type, HUBSPOT_SYNC_URL, "PUT", body=staged_messages
            )
            try:
                response.raise_for_status()
            except HTTPError:
                print(
                    "    Sync message failed with status {} and message {}".format(
                        response.status_code, response.json().get("message")
                    )
                )

    def sync_contacts(self):
        """
        Sync all users with contacts in hubspot
        """
        print("  Syncing users with hubspot contacts...")
        self.bulk_sync_model(User.objects.all(), make_contact_sync_message, "CONTACT")
        print("  Finished")

    def sync_b2b_contacts(self):
        """
        Sync all users with b2b contacts in hubspot
        """
        print("  Syncing users with hubspot b2b contacts...")
        self.bulk_sync_model(
            B2BOrder.objects.all(),
            make_b2b_contact_sync_message,
            "CONTACT",
            use_email=True,
        )
        print("  Finished")

    def sync_products(self):
        """
        Sync all products with products in hubspot
        """
        print("  Syncing products with hubspot products...")
        self.bulk_sync_model(
            Product.objects.filter(productversions__isnull=False),
            make_product_sync_message,
            "PRODUCT",
        )
        print("  Finished")

    def sync_b2b_deals(self):
        """
        Sync all b2b orders with deals in hubspot
        """
        print("  Syncing b2b orders with hubspot deals...")
        self.bulk_sync_model(B2BOrder.objects.all(), make_b2b_deal_sync_message, "DEAL")
        print("  Finished")

    def sync_b2b_product_item(self):
        """
        Sync b2b deal product with line_items in hubspot
        """
        print("  Syncing b2b product with hubspot line items...")
        self.bulk_sync_model(
            B2BOrder.objects.all(), make_b2b_product_sync_message, "LINE_ITEM"
        )
        print("  Finished")

    def sync_deals(self):
        """
        Sync all orders with deals in hubspot
        """
        print("  Syncing orders with hubspot deals...")
        self.bulk_sync_model(Order.objects.all(), make_deal_sync_message, "DEAL")
        print("  Finished")

    def sync_line_items(self):
        """
        Sync all lines with line_items in hubspot
        """
        print("  Syncing lines with hubspot line items...")
        self.bulk_sync_model(
            Line.objects.all(), make_line_item_sync_message, "LINE_ITEM"
        )
        print("  Finished")

    def sync_all(self):
        """
        Sync all Users, Orders, Products, and Lines with Hubspot.
        """
        self.sync_contacts()
        self.sync_products()
        self.sync_deals()
        self.sync_line_items()
        self.sync_b2b_contacts()
        self.sync_b2b_deals()
        self.sync_b2b_product_item()

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
            "--b2bdeals",
            "--b2borders",
            dest="sync_b2b_deals",
            action="store_true",
            help="Sync all b2b orders",
        )
        parser.add_argument(
            "--lines",
            "--line-items",
            dest="sync_line_items",
            action="store_true",
            help="Sync all lines",
        )
        parser.add_argument(
            "--b2bproducts",
            dest="sync_b2b_product",
            action="store_true",
            help="Sync b2b products",
        )
        parser.add_argument(
            "--b2bcontacts",
            dest="sync_b2b_contacts",
            action="store_true",
            help="Sync b2b contacts",
        )

    def handle(self, *args, **options):
        print("Syncing with hubspot...")
        if not (
            options["sync_contacts"]
            or options["sync_products"]
            or options["sync_deals"]
            or options["sync_line_items"]
            or options["sync_b2b_deals"]
            or options["sync_b2b_product"]
            or options["sync_b2b_contacts"]
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
            if options["sync_b2b_deals"]:
                self.sync_b2b_deals()
            if options["sync_b2b_product"]:
                self.sync_b2b_product_item()
            if options["sync_b2b_contacts"]:
                self.sync_b2b_contacts()

        print("Hubspot sync complete")
