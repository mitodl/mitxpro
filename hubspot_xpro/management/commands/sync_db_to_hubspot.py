"""
Management command to sync all Users, Orders, Products, and Lines with Hubspot
and Line Items
"""

import sys

from django.contrib.contenttypes.models import ContentType
from django.core.management import BaseCommand
from mitol.common.utils import now_in_utc
from mitol.hubspot_api.api import HubspotObjectType

from ecommerce.models import Line, Order, Product
from hubspot_xpro.tasks import (
    batch_upsert_associations,
    batch_upsert_hubspot_b2b_deals,
    batch_upsert_hubspot_objects,
)
from users.models import User


class Command(BaseCommand):
    """
    Command to sync all Users, Orders, Products, and Lines with Hubspot
    """

    create = None
    object_ids = None
    help = (
        "Sync all Users, Orders, Products, and Lines with Hubspot. Hubspot API key must be set and Hubspot settings"
        "must be configured with configure_hubspot_settings"
    )

    def sync_contacts(self):
        """
        Sync all users with contacts in hubspot
        """
        sys.stdout.write("Syncing users with hubspot contacts...\n")
        task = batch_upsert_hubspot_objects.delay(
            HubspotObjectType.CONTACTS.value,
            ContentType.objects.get_for_model(User).model,
            User._meta.app_label,  # noqa: SLF001
            create=self.create,
        )
        start = now_in_utc()
        task.get()
        total_seconds = (now_in_utc() - start).total_seconds()
        self.stdout.write(
            f"Syncing of users to hubspot contacts finished, took {total_seconds} seconds\n"
        )

    def sync_products(self):
        """
        Sync all products with products in hubspot
        """
        sys.stdout.write("  Syncing products with hubspot products...\n")
        task = batch_upsert_hubspot_objects.delay(
            HubspotObjectType.PRODUCTS.value,
            ContentType.objects.get_for_model(Product).model,
            Product._meta.app_label,  # noqa: SLF001
            create=self.create,
        )
        start = now_in_utc()
        task.get()
        total_seconds = (now_in_utc() - start).total_seconds()
        self.stdout.write(
            "Syncing of products to hubspot finished, took {} seconds\n".format(  # noqa: UP032
                total_seconds
            )
        )

    def sync_b2b_deals(self):
        """
        Sync all b2b orders with deals in hubspot
        """
        sys.stdout.write("  Syncing b2b orders with hubspot deals...\n")
        task = batch_upsert_hubspot_b2b_deals.delay(self.create)
        start = now_in_utc()
        task.get()
        total_seconds = (now_in_utc() - start).total_seconds()
        self.stdout.write(
            f"Syncing of b2b orders/lines to hubspot finished, took {total_seconds} seconds\n"
        )

    def sync_deals(self):
        """
        Sync all orders with deals in hubspot
        """
        sys.stdout.write("  Syncing orders with hubspot deals...\n")
        task = batch_upsert_hubspot_objects.delay(
            HubspotObjectType.DEALS.value,
            ContentType.objects.get_for_model(Order).model,
            Order._meta.app_label,  # noqa: SLF001
            self.create,
            object_ids=self.object_ids,
        )
        start = now_in_utc()
        task.get()
        total_seconds = (now_in_utc() - start).total_seconds()
        self.stdout.write(
            f"Syncing of orders/lines to hubspot finished, took {total_seconds} seconds\n"
        )

    def sync_lines(self):
        """
        Sync all orders with line_items in hubspot
        """
        sys.stdout.write("  Syncing order lines with hubspot line_items...\n")
        task = batch_upsert_hubspot_objects.delay(
            HubspotObjectType.LINES.value,
            ContentType.objects.get_for_model(Line).model,
            Line._meta.app_label,  # noqa: SLF001
            self.create,
            object_ids=self.object_ids,
        )
        start = now_in_utc()
        task.get()
        total_seconds = (now_in_utc() - start).total_seconds()
        self.stdout.write(
            f"Syncing of order lines to hubspot finished, took {total_seconds} seconds\n"
        )

    def sync_associations(self):
        """
        Sync all deal associations in hubspot
        """
        sys.stdout.write("  Syncing deal associations with hubspot...\n")
        task = batch_upsert_associations.delay(order_ids=self.object_ids)
        start = now_in_utc()
        task.get()
        total_seconds = (now_in_utc() - start).total_seconds()
        self.stdout.write(
            f"Syncing of deal associations to hubspot finished, took {total_seconds} seconds\n"
        )

    def sync_all(self):
        """
        Sync all Users, Products, Orders and Lines with Hubspot.
        All products and contacts should be synced before syncing deals/line items.
        """
        self.sync_contacts()
        self.sync_products()
        self.sync_b2b_deals()
        self.sync_deals()
        self.sync_lines()
        self.sync_associations()

    def add_arguments(self, parser):
        """
        Definition of arguments this command accepts
        """
        parser.add_argument(
            "--ids",
            type=int,
            help="List of object ids to process, must be used for a specific object model",
            nargs="+",
            required=False,
        )
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
            "--line_items",
            dest="sync_lines",
            action="store_true",
            help="Sync all order line items",
        )
        parser.add_argument(
            "--associations",
            dest="sync_associations",
            action="store_true",
            help="Sync all order associations",
        )
        parser.add_argument(
            "mode",
            type=str,
            nargs="?",
            choices=["create", "update"],
            help="create or update",
        )

    def handle(self, *args, **options):  # noqa: ARG002
        if not options["mode"]:
            sys.stderr.write("You must specify mode ('create' or 'update')\n")
            sys.exit(1)
        self.create = options["mode"].lower() == "create"
        self.object_ids = options["ids"]

        sys.stdout.write("Syncing with hubspot...\n")
        if not (
            options["sync_contacts"]
            or options["sync_products"]
            or options["sync_deals"]
            or options["sync_lines"]
            or options["sync_b2b_deals"]
            or options["sync_associations"]
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
            if options["sync_lines"]:
                self.sync_lines()
            if options["sync_b2b_deals"]:
                self.sync_b2b_deals()
            if options["sync_associations"]:
                self.sync_associations()
        sys.stdout.write("Hubspot sync complete\n")
