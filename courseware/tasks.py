"""Courseware tasks"""
from mitxpro.celery import app
from courseware import api
from users.api import get_user_by_id
from users.models import User


@app.task(acks_late=True)
def create_user_from_id(user_id):
    """Loads user by id and calls the API method to create the user in edX"""
    user = get_user_by_id(user_id)
    api.create_user(user)


# To be removed after this has been deployed in all envs
@app.task()
def create_edx_user_from_id(user_id):
    """Backwards-compatibility for celery to forward to the new task name"""
    create_user_from_id.delay(user_id)


@app.task(acks_late=True)
def retry_failed_edx_enrollments():
    """Retries failed edX enrollments"""
    successful_enrollments = api.retry_failed_edx_enrollments()
    return [
        (enrollment.user.email, enrollment.run.courseware_id)
        for enrollment in successful_enrollments
    ]


@app.task(acks_late=True)
def repair_faulty_courseware_users():
    """Calls the API method to repair faulty courseware users"""
    repaired_users = api.repair_faulty_courseware_users()
    return [user.email for user in repaired_users]


@app.task(acks_late=True)
def change_edx_user_email_async(user_id):
    """
    Task to change edX user email in the background to avoid database level locks
    """
    user = User.objects.get(id=user_id)
    api.update_edx_user_email(user)


@app.task(acks_late=True)
def change_edx_user_name_async(user_id):
    """
    Task to change edX user name in the background to avoid database level locks
    """
    user = User.objects.get(id=user_id)
    api.update_edx_user_name(user)
