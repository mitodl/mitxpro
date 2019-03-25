"""Courseware tasks"""
from django.contrib.auth import get_user_model

from mitxpro.celery import app
from courseware.api import create_edx_user


@app.task()
def create_edx_user_from_id(user_id):
    """Loads user by id and calls the API method to create the user in edX"""
    user = get_user_model().objects.get(id=user_id)
    create_edx_user(user)
