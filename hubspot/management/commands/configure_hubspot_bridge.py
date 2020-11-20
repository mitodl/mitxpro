"""
Management command to configure the Hubspot ecommerce bridge which handles syncing Contacts, Deals, Products,
and Line Items
"""
import json
from django.core.management import BaseCommand

from ecommerce import models
from hubspot.api import (
    send_hubspot_request,
    property_group_exists,
    sync_property_group,
    sync_object_property,
    delete_object_property,
    delete_property_group,
    object_property_exists,
)

# Hubspot ecommerce settings define which hubspot properties are mapped with which
# local properties when objects are synced.
# See https://developers.hubspot.com/docs/methods/ecomm-bridge/ecomm-bridge-overview for more details
from hubspot.serializers import ORDER_TYPE_B2B, ORDER_TYPE_B2C

CUSTOM_ECOMMERCE_PROPERTIES = {
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
                "name": "discount_percent",
                "label": "Percent Discount",
                "description": "Percentage off regular price",
                "groupName": "coupon",
                "type": "number",
                "fieldType": "text",
            },
            {
                "name": "num_seats",
                "label": "Number of seats",
                "description": "Total number of seats to purchase",
                "groupName": "dealinformation",
                "type": "number",
                "fieldType": "text",
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
                "name": "payment_type",
                "label": "Payment Type",
                "description": "type of payment transaction",
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
                "name": "product_id",
                "label": "Product Id",
                "description": "The product id of the latest product version",
                "groupName": "lineiteminformation",
                "type": "string",
                "fieldType": "text",
            },
        ],
    },
}

HUBSPOT_ECOMMERCE_SETTINGS = {
    "enabled": True,
    "productSyncSettings": {
        "properties": [
            {
                "propertyName": "title",
                "targetHubspotProperty": "name",
                "dataType": "STRING",
            },
            {
                "propertyName": "price",
                "targetHubspotProperty": "price",
                "dataType": "NUMBER",
            },
            {
                "propertyName": "description",
                "targetHubspotProperty": "description",
                "dataType": "STRING",
            },
        ]
    },
    "contactSyncSettings": {
        "properties": [
            {
                "propertyName": "email",
                "targetHubspotProperty": "email",
                "dataType": "STRING",
            },
            {
                "propertyName": "name",
                "targetHubspotProperty": "name",
                "dataType": "STRING",
            },
            {
                "propertyName": "first_name",
                "targetHubspotProperty": "firstname",
                "dataType": "STRING",
            },
            {
                "propertyName": "last_name",
                "targetHubspotProperty": "lastname",
                "dataType": "STRING",
            },
            {
                "propertyName": "street_address",
                "targetHubspotProperty": "address",
                "dataType": "STRING",
            },
            {
                "propertyName": "city",
                "targetHubspotProperty": "city",
                "dataType": "STRING",
            },
            {
                "propertyName": "country",
                "targetHubspotProperty": "country",
                "dataType": "STRING",
            },
            {
                "propertyName": "state_or_territory",
                "targetHubspotProperty": "state",
                "dataType": "STRING",
            },
            {
                "propertyName": "postal_code",
                "targetHubspotProperty": "zip",
                "dataType": "STRING",
            },
            {
                "propertyName": "birth_year",
                "targetHubspotProperty": "birth_year",
                "dataType": "STRING",
            },
            {
                "propertyName": "gender",
                "targetHubspotProperty": "gender",
                "dataType": "STRING",
            },
            {
                "propertyName": "company",
                "targetHubspotProperty": "company",
                "dataType": "STRING",
            },
            {
                "propertyName": "company_size",
                "targetHubspotProperty": "company_size",
                "dataType": "STRING",
            },
            {
                "propertyName": "industry",
                "targetHubspotProperty": "industry",
                "dataType": "STRING",
            },
            {
                "propertyName": "job_title",
                "targetHubspotProperty": "jobtitle",
                "dataType": "STRING",
            },
            {
                "propertyName": "job_function",
                "targetHubspotProperty": "job_function",
                "dataType": "STRING",
            },
            {
                "propertyName": "years_experience",
                "targetHubspotProperty": "years_experience",
                "dataType": "STRING",
            },
            {
                "propertyName": "leadership_level",
                "targetHubspotProperty": "leadership_level",
                "dataType": "STRING",
            },
            {
                "propertyName": "highest_education",
                "targetHubspotProperty": "highest_education",
                "dataType": "STRING",
            },
        ]
    },
    "dealSyncSettings": {
        "properties": [
            {
                "propertyName": "name",
                "targetHubspotProperty": "dealname",
                "dataType": "STRING",
            },
            {
                "propertyName": "amount",
                "targetHubspotProperty": "amount",
                "dataType": "NUMBER",
            },
            {
                "propertyName": "status",
                "targetHubspotProperty": "status",
                "dataType": "STRING",
            },
            {
                "propertyName": "discount_amount",
                "targetHubspotProperty": "ip__ecomm_bridge__discount_amount",
                "dataType": "NUMBER",
            },
            {
                "propertyName": "close_date",
                "targetHubspotProperty": "closedate",
                "dataType": "STRING",
            },
            {
                "propertyName": "coupon_code",
                "targetHubspotProperty": "coupon_code",
                "dataType": "STRING",
            },
            {
                "propertyName": "purchaser",
                "targetHubspotProperty": "hs_assoc__contact_ids",
                "dataType": "STRING",
            },
            {
                "propertyName": "stage",
                "targetHubspotProperty": "dealstage",
                "dataType": "STRING",
            },
            {
                "propertyName": "company",
                "targetHubspotProperty": "company",
                "dataType": "STRING",
            },
            {
                "propertyName": "payment_type",
                "targetHubspotProperty": "payment_type",
                "dataType": "STRING",
            },
            {
                "propertyName": "payment_transaction",
                "targetHubspotProperty": "payment_transaction",
                "dataType": "STRING",
            },
            {
                "propertyName": "discount_percent",
                "targetHubspotProperty": "discount_percent",
                "dataType": "NUMBER",
            },
            {
                "propertyName": "order_type",
                "targetHubspotProperty": "order_type",
                "dataType": "STRING",
            },
            {
                "propertyName": "num_seats",
                "targetHubspotProperty": "num_seats",
                "dataType": "NUMBER",
            },
        ]
    },
    "lineItemSyncSettings": {
        "properties": [
            {
                "propertyName": "order",
                "targetHubspotProperty": "hs_assoc__deal_id",
                "dataType": "STRING",
            },
            {
                "propertyName": "product",
                "targetHubspotProperty": "hs_assoc__product_id",
                "dataType": "STRING",
            },
            {
                "propertyName": "quantity",
                "targetHubspotProperty": "quantity",
                "dataType": "NUMBER",
            },
            {
                "propertyName": "status",
                "targetHubspotProperty": "status",
                "dataType": "STRING",
            },
            {
                "propertyName": "product_id",
                "targetHubspotProperty": "product_id",
                "dataType": "STRING",
            },
        ]
    },
}

HUBSPOT_INSTALL_PATH = "/extensions/ecomm/v1/installs"
HUBSPOT_SETTINGS_PATH = "/extensions/ecomm/v1/settings"


def install_hubspot_ecommerce_bridge():
    """Install the Hubspot ecommerce bridge for the api key specified in settings"""
    response = send_hubspot_request("", HUBSPOT_INSTALL_PATH, "POST")
    response.raise_for_status()
    return response


def uninstall_hubspot_ecommerce_bridge():
    """Install the Hubspot ecommerce bridge for the api key specified in settings"""
    response = send_hubspot_request("uninstall", HUBSPOT_INSTALL_PATH, "POST")
    response.raise_for_status()
    return response


def get_hubspot_installation_status():
    """Get the Hubspot ecommerce bridge installation status for the api key specified in settings"""
    response = send_hubspot_request("status", HUBSPOT_INSTALL_PATH, "GET")
    response.raise_for_status()
    return response


def configure_hubspot_settings():
    """Configure the current Hubspot ecommerce bridge settings for the api key specified in settings"""
    response = send_hubspot_request(
        "", HUBSPOT_SETTINGS_PATH, "PUT", body=HUBSPOT_ECOMMERCE_SETTINGS
    )
    response.raise_for_status()
    return response


def install_custom_properties():
    """Create or update all custom properties and groups"""
    for object_type in CUSTOM_ECOMMERCE_PROPERTIES:
        for group in CUSTOM_ECOMMERCE_PROPERTIES[object_type]["groups"]:
            sync_property_group(object_type, group["name"], group["label"])
        for obj_property in CUSTOM_ECOMMERCE_PROPERTIES[object_type]["properties"]:
            sync_object_property(object_type, obj_property)


def uninstall_custom_properties():
    """Delete all custom properties and groups"""
    for object_type in CUSTOM_ECOMMERCE_PROPERTIES:
        for obj_property in CUSTOM_ECOMMERCE_PROPERTIES[object_type]["properties"]:
            if object_property_exists(object_type, obj_property):
                delete_object_property(object_type, obj_property)
        for group in CUSTOM_ECOMMERCE_PROPERTIES[object_type]["groups"]:
            if property_group_exists(object_type, group):
                delete_property_group(object_type, group)


def get_hubspot_settings():
    """Get the current Hubspot ecommerce bridge settings for the api key specified in settings"""
    response = send_hubspot_request("", HUBSPOT_SETTINGS_PATH, "GET")
    response.raise_for_status()
    return response


class Command(BaseCommand):
    """
    Command to configure the Hubspot ecommerce bridge which will handle syncing Hubspot Products, Deals, Line Items,
    and Contacts with the MITxPro Products, Orders, and Users
    """

    help = (
        "Install the Hubspot Ecommerce Bridge if it is not already installed and configure the settings based on "
        "the given file. Make sure a HUBSPOT_API_KEY is set in settings and HUBSPOT_ECOMMERCE_SETTINGS are "
        "configured in ecommerce/management/commands/configure_hubspot_bridge.py"
    )

    def add_arguments(self, parser):
        """
        Definition of arguments this command accepts
        """
        parser.add_argument(
            "--uninstall", action="store_true", help="Uninstall the Ecommerce Bridge"
        )

        parser.add_argument(
            "--status",
            action="store_true",
            help="Get the current status of the Ecommerce Bridge installation",
        )

    def handle(self, *args, **options):
        print(
            "Checking Hubspot Ecommerce Bridge installation for given Hubspot API Key..."
        )
        installation_status = json.loads(get_hubspot_installation_status().text)
        print(installation_status)
        if options["status"]:
            print(f"Install completed: {installation_status['installCompleted']}")
            print(
                f"Ecommerce Settings enabled: {installation_status['ecommSettingsEnabled']}"
            )
        elif options["uninstall"]:
            if installation_status["installCompleted"]:
                print("Uninstalling Ecommerce Bridge...")
                uninstall_hubspot_ecommerce_bridge()
                print("Uninstalling cutsom groups and properties...")
                uninstall_custom_properties()
                print("Uninstall successful")
                return
            else:
                print("Ecommerce Bridge is not installed")
                return
        else:
            print("Configuring settings...")
            configure_hubspot_settings()
            print("Configuring custom groups and properties...")
            install_custom_properties()
            print("Settings and custom properties configured")
