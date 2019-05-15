"""
User tasks
"""
import json

import requests
from django.conf import settings

from mitxpro.celery import app


HUBSPOT_API_BASE_URL = 'https://api.hubapi.com'


def make_hubspot_contact_update(user):
    """
    Generate update data to be passed in the hubspot request
    """
    return {
        "email": user.email,
        "properties": [
            {
                "property": "firstname",
                "value": user.name,
            },
            # This code is waiting on PR #236
            # {
            #     "property": "company",
            #     "value": user.profile.company,
            # },
            # {
            #     "property": "jobtitle",
            #     "value": user.job_title,
            # },
            # {
            #     "property": "gender",
            #     "value": user.profile.gender
            # },
        ]
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

    url = f'{HUBSPOT_API_BASE_URL}/contacts/v1/contact/batch/?hapikey={api_key}'
    data = json.dumps(contacts)
    headers = {'Content-Type': 'application/json'}

    return requests.post(url=url, data=data, headers=headers)


@app.task()
def sync_user_with_hubspot(user, api_key=settings.HUBSPOT_API_KEY):
    """
    Sync a batch of users with hubspot
    """
    if not api_key:
        return
    url = f'{HUBSPOT_API_BASE_URL}/contacts/v1/contact/createOrUpdate/email/{user.email}?hapikey={api_key}'
    data = json.dumps(make_hubspot_contact_update(user))
    headers = {'Content-Type': 'application/json'}

    return requests.post(url=url, data=data, headers=headers)
