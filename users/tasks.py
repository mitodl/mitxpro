"""
User tasks
"""
import json

import requests
from django.conf import settings
from rest_framework import status

from mitxpro.celery import app
from users.exceptions import HubspotUserSyncError
from users.models import User

HUBSPOT_API_BASE_URL = "https://api.hubapi.com"


hubspot_property_mapping = {
    "firstname": {"model": "user", "field": "name"},
    "company": {"model": "profile", "field": "company"},
    "jobtitle": {"model": "profile", "field": "job_title"},
    "gender": {"model": "profile", "field": "gender"},
}


def map_hubspot_property(user, key, mapping):
    """
    Translate user database fields into Hubspot contact properties based on the above mapping
    Args:
        user (User): a users.models.User object
        key (str): name of a contact property
        mapping (dict): contact properties map
    Returns:
        dict: a hubspot property map for the specified key
    """
    prop = {
        "property": key,
        "value": mapping["default"] if "default" in mapping else "",
    }
    if mapping["model"] == "user":
        prop["value"] = getattr(user, mapping["field"])
    else:
        if hasattr(user, mapping["model"]):
            prop["value"] = getattr(getattr(user, mapping["model"]), mapping["field"])
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
def sync_users_batch_with_hubspot(user_ids_batch, api_key=settings.HUBSPOT_API_KEY):
    """
    Sync a batch of users with hubspot
    """
    if not api_key:
        return
    contacts = []
    for user_id in user_ids_batch:
        user = User.objects.get(id=user_id)
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
def sync_user_with_hubspot(user_id, api_key=settings.HUBSPOT_API_KEY):
    """
    Sync a batch of users with hubspot
    """
    if not api_key:
        return
    user = User.objects.get(id=user_id)
    url = f"{HUBSPOT_API_BASE_URL}/contacts/v1/contact/createOrUpdate/email/{user.email}?hapikey={api_key}"
    data = json.dumps(make_hubspot_contact_update(user))
    headers = {"Content-Type": "application/json"}

    response = requests.post(url=url, data=data, headers=headers)
    if response.status_code != status.HTTP_200_OK:
        raise HubspotUserSyncError(
            f"Error syncing MITxPro users with Hubspot, got status_code={response.status_code}"
        )
