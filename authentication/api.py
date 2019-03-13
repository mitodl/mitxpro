"""Authentication api"""
from django.contrib.auth import get_user_model

User = get_user_model()


def create_user(username, email, user_extra=None):
    """
    Ensures the user exists

    Args:
        email (str): the user's email

    Returns:
        User: the user
    """
    defaults = {}

    if user_extra is not None:
        defaults.update(user_extra)

    # this takes priority over a passed in value
    defaults.update({"username": username})

    user, _ = User.objects.get_or_create(email=email, defaults=defaults)

    return user
