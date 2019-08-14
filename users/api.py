"""Users api"""
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.contrib.auth import get_user_model

from mitxpro.utils import first_or_none

User = get_user_model()


def get_user_by_id(user_id):
    """
    Gets a User by id

    Args:
        user_id (int): the user id to fetch

    Returns:
        users.models.User: the user found by id
    """
    return User.objects.get(id=user_id)


def fetch_user(user_property):
    """
    Attempts to fetch a user based on several properties

    Args:
        user_property (Union[str, int]): The id, email, or username of some User
    Returns:
        User: A user that matches the given property
    """
    if isinstance(user_property, int):
        return User.objects.get(id=user_property)
    elif user_property.isdigit():
        return User.objects.get(id=int(user_property))
    else:
        try:
            validate_email(user_property)
            return User.objects.get(email=user_property)
        except ValidationError:
            return User.objects.get(username=user_property)


def fetch_users(user_properties):
    """
    Attempts to fetch a set of users based on several properties. The property being searched
    (i.e.: id, email, or username) is assumed to be the same for all of the given values, so the
    property type is determined for the first element, then used for all of the values provided.

    Args:
        user_properties (iterable of Union[str, int]): The ids, emails, or usernames of the target Users
    Returns:
        User queryset: Users that match the given properties
    """
    first_user_property = first_or_none(user_properties)
    if not first_user_property:
        return None
    if isinstance(first_user_property, int):
        filter_prop, filter_values = ("id", user_properties)
    elif first_user_property.isdigit():
        filter_prop, filter_values = ("id", map(int, user_properties))
    else:
        try:
            validate_email(first_user_property)
            filter_prop, filter_values = ("email", user_properties)
        except ValidationError:
            filter_prop, filter_values = ("username", user_properties)
    user_qset = User.objects.filter(**{"{}__in".format(filter_prop): filter_values})
    if not user_qset.count() == len(user_properties):
        valid_values = user_qset.values_list(filter_prop, flat=True)
        invalid_values = set(filter_values) - set(valid_values)
        raise User.DoesNotExist(
            "Could not find Users with these '{}' values: {}".format(
                filter_prop, sorted(list(invalid_values))
            )
        )
    return user_qset
