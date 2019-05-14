"""
User tasks
"""
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
                "property": "name",
                "value": user.name,
            },
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
def sync_users_batch_with_hubspot(users_batch):
    """
    Sync a batch of users with hubspot
    """
    api_key = settings.HUBSPOT_API_KEY
    if not api_key:
        return
    contacts = []
    for user in users_batch:
        if not hasattr(user, 'profile'):
            continue

        contacts.append(make_hubspot_contact_update(user))

    response = requests.post(
            f'{HUBSPOT_API_BASE_URL}/contacts/v1/contact/batch/?hapikey={api_key}',
            contacts,
            format='json'
        )
    # print(response)


@app.task()
def sync_user_with_hubspot(user):
    """
    Sync a batch of users with hubspot
    """
    api_key = settings.HUBSPOT_API_KEY
    if not api_key:
        return

    response = requests.post(
        f'{HUBSPOT_API_BASE_URL}/contacts/v1/contact/email/{user.email}/profile?hapikey={api_key}',
        make_hubspot_contact_update(user),
    )
    # print(response)
