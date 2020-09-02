"""Authentication api"""
from importlib import import_module

from django.conf import settings
from django.contrib.auth import SESSION_KEY, BACKEND_SESSION_KEY, HASH_SESSION_KEY
from django.db import IntegrityError

from users.utils import is_duplicate_username_error
from users.api import find_available_username


USERNAME_COLLISION_ATTEMPTS = 10


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

    session[SESSION_KEY] = user._meta.pk.value_to_string(user)
    session[BACKEND_SESSION_KEY] = "django.contrib.auth.backends.ModelBackend"
    session[HASH_SESSION_KEY] = user.get_session_auth_hash()
    session.save()

    return session


def create_user_with_generated_username(serializer, initial_username):
    """
    Creates a User with a given username, and if there is a User that already has that username,
    finds an available username and reattempts the User creation.

    Args:
        serializer (UserSerializer instance): A user serializer instance that has been instantiated
            with user data and has passed initial validation
        initial_username (str): The initial username to attempt to save the User with
    Returns:
        User or None: The created User (or None if the User could not be created in the
            number of retries allowed)
    """
    created_user = None
    username = initial_username
    attempts = 0

    if len(username) < 2:
        username = username + "11"

    while created_user is None and attempts < USERNAME_COLLISION_ATTEMPTS:
        try:
            created_user = serializer.save(username=username)
        except IntegrityError as exc:
            if not is_duplicate_username_error(exc):
                raise
            username = find_available_username(initial_username)
        finally:
            attempts += 1
    return created_user
