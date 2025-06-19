"""Users api"""

import operator
from functools import reduce

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db.models import Q

from mitxpro.utils import first_or_none, unique, unique_ignore_case

User = get_user_model()

CASE_INSENSITIVE_SEARCHABLE_FIELDS = {"email"}


def get_user_by_id(user_id):
    """
    Get a User by id

    Args:
        user_id (int): the user id to fetch

    Returns:
        users.models.User: the user found by id
    """
    return User.objects.get(id=user_id)


def _is_case_insensitive_searchable(field_name):
    """
    Indicate whether or not a given field in the User model is a string field

    Args:
        field_name (str): The name of the User field
    Return:
        bool: True if the given User field is a string field
    """
    return field_name in CASE_INSENSITIVE_SEARCHABLE_FIELDS


def _determine_filter_field(user_property):
    """
    Assesses the value provided to search for a User and returns the field name that should
    be used for the query (e.g.: "id", "username", "email")

    Args:
        user_property (str): The id/username/email value being used to find Users
    Returns:
        str: User field name that should be used for a query based on the value provided
    """
    if isinstance(user_property, int) or user_property.isdigit():
        return "id"
    else:
        try:
            validate_email(user_property)
            return "email"  # noqa: TRY300
        except ValidationError:
            return "username"


def fetch_user(filter_value, ignore_case=True):  # noqa: FBT002
    """
    Attempt to fetch a user based on several properties

    Args:
        filter_value (Union[str, int]): The id, email, or username of some User
        ignore_case (bool): If True, the User query will be case-insensitive
    Returns:
        User: A user that matches the given property
    """
    filter_field = _determine_filter_field(filter_value)

    if _is_case_insensitive_searchable(filter_field) and ignore_case:
        query = {f"{filter_field}__iexact": filter_value}
    else:
        query = {filter_field: filter_value}
    try:
        return User.objects.get(**query)
    except User.DoesNotExist as e:
        raise User.DoesNotExist(
            "Could not find User with {}={} ({})".format(  # noqa: EM103
                filter_field,
                filter_value,
                "case-insensitive" if ignore_case else "case-sensitive",
            )
        ) from e


def fetch_users(filter_values, ignore_case=True):  # noqa: FBT002
    """
    Attempt to fetch a set of users based on several properties. The property being searched
    (i.e.: id, email, or username) is assumed to be the same for all of the given values, so the
    property type is determined for the first element, then used for all of the values provided.

    Args:
        filter_values (iterable of Union[str, int]): The ids, emails, or usernames of the target Users
        ignore_case (bool): If True, the User query will be case-insensitive
    Returns:
        User queryset or None: Users that match the given properties
    """

    first_user_property = first_or_none(filter_values)
    if not first_user_property:
        return None
    filter_field = _determine_filter_field(first_user_property)
    is_case_insensitive_searchable = _is_case_insensitive_searchable(filter_field)

    unique_filter_values = set(
        unique_ignore_case(filter_values)
        if is_case_insensitive_searchable and ignore_case
        else unique(filter_values)
    )
    if len(filter_values) > len(unique_filter_values):
        raise ValidationError(
            "Duplicate values provided ({})".format(  # noqa: EM103, UP032
                set(filter_values).intersection(unique_filter_values)
            )
        )

    if is_case_insensitive_searchable and ignore_case:
        query = reduce(
            operator.or_,
            (
                Q(**{f"{filter_field}__iexact": filter_value})
                for filter_value in filter_values
            ),
        )
        user_qset = User.objects.filter(query)
    else:
        user_qset = User.objects.filter(**{f"{filter_field}__in": filter_values})
    if user_qset.count() != len(filter_values):
        valid_values = user_qset.values_list(filter_field, flat=True)
        invalid_values = set(filter_values) - set(valid_values)
        raise User.DoesNotExist(
            "Could not find Users with these '{}' values ({}): {}".format(  # noqa: EM103
                filter_field,
                "case-insensitive" if ignore_case else "case-sensitive",
                sorted(invalid_values),
            )
        )
    return user_qset
