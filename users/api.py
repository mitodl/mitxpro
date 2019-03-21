"""Users api"""
from django.contrib.auth import get_user_model


def get_user_by_id(user_id):
    """
    Gets a User by id

    Args:
        user_id (int): the user id to fetch

    Returns:
        users.models.User: the user found by id
    """
    return get_user_model().objects.get(id=user_id)
