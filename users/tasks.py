"""
User tasks
"""
import json

import requests
from django.conf import settings
from rest_framework import status

from mitxpro.celery import app
from users.exceptions import HubspotUserSyncError

HUBSPOT_API_BASE_URL = "https://api.hubapi.com"


hubspot_property_mapping = {
    "firstname": {"model": "user", "field": "name"},
    "company": {"model": "profile", "field": "company"},
    "jobtitle": {"model": "profile", "field": "job_title"},
    "gender": {"model": "profile", "field": "gender"},
}


def map_hubspot_property(user, key, mapping):
    """
    Map a user to a hubspot contact dict
    :param user: user object to map
    :param key: property name in hubspot
    :param mapping: dict containing model and field to find value, optionally contains 'default'
    :return: dictionary in the form expected by hubspot api:
        { 'properties': [
            {'property': 'property_name',
            'value': value},
            ...]
        }
    """
    prop = {
        "property": key,
        "value": mapping["default"] if "default" in mapping else "",
    }
    if mapping["model"] == "profile" and hasattr(user, "profile"):
        prop["value"] = getattr(user.profile, mapping["field"])
    elif mapping["model"] == "user":
        prop["value"] = getattr(user, mapping["field"])
    return prop


def make_hubspot_contact_update(user):
    """
    Generate update data to be passed in the hubspot request
    """
    return {
        "email": user.email,
        "properties": [
            map_hubspot_property(user, key, mapping)
            for key, mapping in hubspot_property_mapping.items()
        ],
    }


@app.task()
def sync_users_batch_with_hubspot(users_batch, api_key=settings.HUBSPOT_API_KEY):
    """
    Sync a batch of users with hubspot
    """
    if not api_key:
        return
    contacts = []
    for user in users_batch:
        contacts.append(make_hubspot_contact_update(user))

    url = f"{HUBSPOT_API_BASE_URL}/contacts/v1/contact/batch/?hapikey={api_key}"
    data = json.dumps(contacts)
    headers = {"Content-Type": "application/json"}

    response = requests.post(url=url, data=data, headers=headers)
    if response.status_code != status.HTTP_202_ACCEPTED:
        raise HubspotUserSyncError(
            f"Error syncing MITxPro users with Hubspot, got status_code={response.status_code}"
        )


@app.task()
def sync_user_with_hubspot(user, api_key=settings.HUBSPOT_API_KEY):
    """
    Sync a batch of users with hubspot
    """
    if not api_key:
        return
    url = f"{HUBSPOT_API_BASE_URL}/contacts/v1/contact/createOrUpdate/email/{user.email}?hapikey={api_key}"
    data = json.dumps(make_hubspot_contact_update(user))
    headers = {"Content-Type": "application/json"}

    response = requests.post(url=url, data=data, headers=headers)
    if response.status_code != status.HTTP_200_OK:
        raise HubspotUserSyncError(
            f"Error syncing MITxPro users with Hubspot, got status_code={response.status_code}"
        )
