"""Courseware tasks"""

from mitxpro.celery import app
from courseware.api import create_edx_user, create_edx_auth_token
from users.api import get_user_by_id


@app.task()
def create_edx_user_from_id(user_id):
    """Loads user by id and calls the API method to create the user in edX"""
    user = get_user_by_id(user_id)
    create_edx_user(user)
    create_edx_auth_token(user)
