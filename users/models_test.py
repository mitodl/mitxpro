"""Tests for user models"""
# pylint: disable=too-many-arguments, redefined-outer-name
import factory
from django.core.exceptions import ValidationError
from django.db import transaction
import pytest
import ulid

from courseware.factories import OpenEdxApiAuthFactory, CoursewareUserFactory
from users.factories import UserFactory
from users.models import LegalAddress, User

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    "create_func,exp_staff,exp_superuser,exp_is_active",
    [
        [User.objects.create_user, False, False, False],
        [User.objects.create_superuser, True, True, True],
    ],
)
@pytest.mark.parametrize("username", [None, "user1"])
@pytest.mark.parametrize("password", [None, "pass"])
def test_create_user(
    create_func, exp_staff, exp_superuser, exp_is_active, username, password
):  # pylint: disable=too-many-arguments
    """Test creating a user"""
    email = "uSer@EXAMPLE.com"
    name = "Jane Doe"
    with transaction.atomic():
        user = create_func(username, email=email, name=name, password=password)

    if username is not None:
        assert user.username == username
    else:
        assert isinstance(ulid.parse(user.username), ulid.ULID)
    assert user.email == "uSer@example.com"
    assert user.name == name
    assert user.get_full_name() == name
    assert user.is_staff is exp_staff
    assert user.is_superuser is exp_superuser
    assert user.is_active is exp_is_active
    if password is not None:
        assert user.check_password(password)

    assert LegalAddress.objects.filter(user=user).exists()


@pytest.mark.parametrize(
    "kwargs",
    [
        {"is_staff": False},
        {"is_superuser": False},
        {"is_staff": False, "is_superuser": False},
    ],
)
def test_create_superuser_error(kwargs):
    """Test creating a user"""
    with pytest.raises(ValueError):
        User.objects.create_superuser(
            username=None,
            email="uSer@EXAMPLE.com",
            name="Jane Doe",
            password="abc",
            **kwargs,
        )


@pytest.mark.parametrize(
    "field, value, is_valid",
    [
        ["country", "US", True],
        ["country", "United States", False],
        ["state_or_territory", "US-MA", True],
        ["state_or_territory", "MA", False],
        ["state_or_territory", "Massachusets", False],
    ],
)
def test_legal_address_validation(field, value, is_valid):
    """Verify legal address validation"""
    address = LegalAddress()

    setattr(address, field, value)

    with pytest.raises(ValidationError) as exc:
        address.clean_fields()

    if is_valid:
        assert field not in exc.value.error_dict
    else:
        assert field in exc.value.error_dict


@pytest.mark.django_db
def test_faulty_user_qset():
    """User.faulty_courseware_users should return a User queryset that contains incorrectly configured active Users"""
    users = UserFactory.create_batch(5)
    # An inactive user should not be returned even if they lack auth and courseware user records
    UserFactory.create(is_active=False)
    good_users = users[0:2]
    expected_faulty_users = users[2:]
    OpenEdxApiAuthFactory.create_batch(
        3, user=factory.Iterator(good_users + [users[3]])
    )
    CoursewareUserFactory.create_batch(
        3, user=factory.Iterator(good_users + [users[4]])
    )

    assert set(User.faulty_courseware_users.values_list("id", flat=True)) == {
        user.id for user in expected_faulty_users
    }
