"""
Management command to configure the Hubspot ecommerce bridge which handles syncing Contacts, Deals, Products,
and Line Items
"""
import json
from django.core.management import BaseCommand

from hubspot.api import send_hubspot_request

# Hubspot ecommerce settings define which hubspot properties are mapped with which
# local properties when objects are synced.
# See https://developers.hubspot.com/docs/methods/ecomm-bridge/ecomm-bridge-overview for more details
HUBSPOT_ECOMMERCE_SETTINGS = {
    "enabled": True,
    "productSyncSettings": {
        "properties": [
            {
                "propertyName": "created_on",
                "targetHubspotProperty": "createdate",
                "dataType": "DATETIME",
            },
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
        ]
    },
    "dealSyncSettings": {
        "properties": [
            {
                "propertyName": "status",
                "targetHubspotProperty": "dealstage",
                "dataType": "STRING",
            }
        ]
    },
    "lineItemSyncSettings": {"properties": []},
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
            f"Checking Hubspot Ecommerce Bridge installation for given Hubspot API Key..."
        )
        installation_status = json.loads(get_hubspot_installation_status().text)
        if options["status"]:
            print(f"Install completed: {installation_status['installCompleted']}")
            print(
                f"Ecommerce Settings enabled: {installation_status['ecommSettingsEnabled']}"
            )
        if options["uninstall"]:
            if installation_status["installCompleted"]:
                print("Uninstalling Ecommerce Bridge...")
                uninstall_hubspot_ecommerce_bridge()
                print("Uninstall successful")
                return
            else:
                print("Ecommerce Bridge is not installed")
                return
        if not installation_status["installCompleted"]:
            print(f"Installation not found. Installing now...")
            install_hubspot_ecommerce_bridge()
            print("Install successful")
        else:
            print(f"Installation found")
        if options["status"]:
            print("Getting settings...")
            ecommerce_bridge_settings = json.loads(get_hubspot_settings().text)
            print("Found settings:")
            print(ecommerce_bridge_settings)
        else:
            print(f"Configuring settings...")
            configure_hubspot_settings()
            print(f"Settings configured")
