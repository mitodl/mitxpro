"""Authentication api"""

from importlib import import_module

from django.conf import settings
from django.contrib.auth import BACKEND_SESSION_KEY, HASH_SESSION_KEY, SESSION_KEY


def create_user_session(user):
    """
    Creates a new session for the user based on the configured session engine

    Args:
        user(User): the user for which to create a session

    Returns:
        SessionBase: the created session
    """
    SessionStore = import_module(settings.SESSION_ENGINE).SessionStore

    session = SessionStore()

    session[SESSION_KEY] = user._meta.pk.value_to_string(user)  # noqa: SLF001
    session[BACKEND_SESSION_KEY] = "django.contrib.auth.backends.ModelBackend"
    session[HASH_SESSION_KEY] = user.get_session_auth_hash()
    session.save()

    return session
