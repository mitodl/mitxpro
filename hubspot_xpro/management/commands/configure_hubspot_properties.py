"""
Management command to configure custom Hubspot properties for Contacts, Deals, Products, and Line Items
"""
import sys

from django.core.management import BaseCommand
from mitol.hubspot_api.api import (
    delete_object_property,
    delete_property_group,
    object_property_exists,
    property_group_exists,
    sync_object_property,
    sync_property_group,
)

from ecommerce import models
from hubspot_xpro.serializers import ORDER_TYPE_B2B, ORDER_TYPE_B2C


CUSTOM_ECOMMERCE_PROPERTIES = {
    # defines which hubspot properties are mapped with which local properties when objects are synced.
    # See https://developers.hubspot.com/docs/methods/ecomm-bridge/ecomm-bridge-overview for more details
    "deals": {
        "groups": [{"name": "coupon", "label": "Coupon"}],
        "properties": [
            {
                "name": "order_type",
                "label": "Order Type",
                "description": "B2B or B2C",
                "groupName": "dealinformation",
                "type": "enumeration",
                "fieldType": "select",
                "options": [
                    {
                        "value": ORDER_TYPE_B2B,
                        "label": ORDER_TYPE_B2B,
                        "displayOrder": 0,
                        "hidden": False,
                    },
                    {
                        "value": ORDER_TYPE_B2C,
                        "label": ORDER_TYPE_B2C,
                        "displayOrder": 1,
                        "hidden": False,
                    },
                ],
            },
            {
                "name": "status",
                "label": "Order Status",
                "description": "The current status of the order",
                "groupName": "dealinformation",
                "type": "enumeration",
                "fieldType": "select",
                "options": [
                    {
                        "value": models.Order.FULFILLED,
                        "label": models.Order.FULFILLED,
                        "displayOrder": 0,
                        "hidden": False,
                    },
                    {
                        "value": models.Order.FAILED,
                        "label": models.Order.FAILED,
                        "displayOrder": 1,
                        "hidden": False,
                    },
                    {
                        "value": models.Order.CREATED,
                        "label": models.Order.CREATED,
                        "displayOrder": 0,
                        "hidden": False,
                    },
                    {
                        "value": models.Order.REFUNDED,
                        "label": models.Order.REFUNDED,
                        "displayOrder": 1,
                        "hidden": False,
                    },
                ],
            },
            {
                "name": "num_seats",
                "label": "Number of seats",
                "description": "Total number of seats to purchase",
                "groupName": "dealinformation",
                "type": "number",
                "fieldType": "number",
            },
            {
                "name": "payment_transaction",
                "label": "Payment Transaction ID",
                "description": "ID of payment transaction",
                "groupName": "coupon",
                "type": "string",
                "fieldType": "text",
            },
            {
                "name": "discount_percent",
                "label": "Percent Discount",
                "description": "Percentage off regular price",
                "groupName": "coupon",
                "type": "number",
                "fieldType": "number",
            },
            {
                "name": "discount_amount",
                "label": "Discount savings",
                "description": "The discount on the deal as an amount.",
                "groupName": "coupon",
                "type": "number",
                "fieldType": "number",
            },
            {
                "name": "payment_type",
                "label": "Payment Type",
                "description": "type of payment transaction",
                "groupName": "coupon",
                "type": "string",
                "fieldType": "text",
            },
            {
                "name": "discount_type",
                "label": "Discount Type",
                "description": "Type of discount (percent-off or dollars-off)",
                "groupName": "coupon",
                "type": "string",
                "fieldType": "text",
            },
            {
                "name": "coupon_code",
                "label": "Coupon Code",
                "description": "The coupon code used for the purchase",
                "groupName": "coupon",
                "type": "string",
                "fieldType": "text",
            },
            {
                "name": "company",
                "label": "Company",
                "description": "The company associated with the coupon",
                "groupName": "coupon",
                "type": "string",
                "fieldType": "text",
            },
            {
                "name": "unique_app_id",
                "label": "Unique App ID",
                "description": "The unique app ID for the deal",
                "groupName": "dealinformation",
                "type": "string",
                "fieldType": "text",
                "hasUniqueValue": True,
                "hidden": True,
            },
        ],
    },
    "contacts": {
        "groups": [],
        "properties": [
            {
                "name": "highest_education",
                "label": "Highest Education",
                "description": "Highest education level",
                "groupName": "contactinformation",
                "type": "string",
                "fieldType": "text",
            },
            {
                "name": "birth_year",
                "label": "Year of Birth",
                "description": "Year of birth",
                "groupName": "contactinformation",
                "type": "string",
                "fieldType": "text",
            },
            {
                "name": "leadership_level",
                "label": "Leadership Level",
                "description": "Leadership Level",
                "groupName": "contactinformation",
                "type": "string",
                "fieldType": "text",
            },
            {
                "name": "highest_education",
                "label": "Highest Education",
                "description": "Highest education level",
                "groupName": "contactinformation",
                "type": "string",
                "fieldType": "text",
            },
            {
                "name": "name",
                "label": "Name",
                "description": "Full name",
                "groupName": "contactinformation",
                "type": "string",
                "fieldType": "text",
            },
            {
                "name": "vat_id",
                "label": "VAT ID",
                "description": "Customer VAT ID",
                "groupName": "contactinformation",
                "type": "string",
                "fieldType": "text",
            },
        ],
    },
    "line_items": {
        "groups": [],
        "properties": [
            {
                "name": "status",
                "label": "Order Status",
                "description": "The current status of the order associated with the line item",
                "groupName": "lineiteminformation",
                "type": "enumeration",
                "fieldType": "select",
                "options": [
                    {
                        "value": models.Order.FULFILLED,
                        "label": models.Order.FULFILLED,
                        "displayOrder": 0,
                        "hidden": False,
                    },
                    {
                        "value": models.Order.FAILED,
                        "label": models.Order.FAILED,
                        "displayOrder": 1,
                        "hidden": False,
                    },
                    {
                        "value": models.Order.CREATED,
                        "label": models.Order.CREATED,
                        "displayOrder": 0,
                        "hidden": False,
                    },
                    {
                        "value": models.Order.REFUNDED,
                        "label": models.Order.REFUNDED,
                        "displayOrder": 1,
                        "hidden": False,
                    },
                ],
            },
            {
                "name": "unique_app_id",
                "label": "Unique App ID",
                "description": "The unique app ID for the lineitem",
                "groupName": "lineiteminformation",
                "type": "string",
                "fieldType": "text",
                "hasUniqueValue": True,
                "hidden": True,
            },
        ],
    },
    "products": {
        "groups": [],
        "properties": [
            {
                "name": "unique_app_id",
                "label": "Unique App ID",
                "description": "The unique app ID for the product",
                "groupName": "productinformation",
                "type": "string",
                "fieldType": "text",
                "hasUniqueValue": True,
                "hidden": True,
            },
        ],
    },
}


def upsert_custom_properties():
    """Create or update all custom properties and groups"""
    for object_type in CUSTOM_ECOMMERCE_PROPERTIES:
        for group in CUSTOM_ECOMMERCE_PROPERTIES[object_type]["groups"]:
            sys.stdout.write(f"Adding group {group}\n")
            sync_property_group(object_type, group["name"], group["label"])
        for obj_property in CUSTOM_ECOMMERCE_PROPERTIES[object_type]["properties"]:
            sys.stdout.write(f"Adding property {obj_property}\n")
            sync_object_property(object_type, obj_property)


def delete_custom_properties():
    """Delete all custom properties and groups"""
    for object_type in CUSTOM_ECOMMERCE_PROPERTIES:
        for obj_property in CUSTOM_ECOMMERCE_PROPERTIES[object_type]["properties"]:
            if object_property_exists(object_type, obj_property):
                delete_object_property(object_type, obj_property)
        for group in CUSTOM_ECOMMERCE_PROPERTIES[object_type]["groups"]:
            if property_group_exists(object_type, group):
                delete_property_group(object_type, group)


class Command(BaseCommand):
    """
    Command to create/update or delete custom hubspot object properties and property groups
    """

    help = "Upsert or delete custom properties and property groups for Hubspot objects"

    def add_arguments(self, parser):
        """
        Definition of arguments this command accepts
        """
        parser.add_argument(
            "--delete",
            action="store_true",
            help="Delete custom hubspot properties/groups",
        )

    def handle(self, *args, **options):
        if options["delete"]:
            print("Uninstalling custom groups and properties...")
            delete_custom_properties()
            print("Uninstall successful")
            return
        else:
            print("Configuring custom groups and properties...")
            upsert_custom_properties()
            print("Custom properties configured")
