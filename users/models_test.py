"""Tests for user models"""
import pytest
import ulid

from users.models import User

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("username", [None, "user1"])
@pytest.mark.parametrize("password", [None, "pass"])
def test_create_user(username, password):
    """Test creating a user"""
    email = "uSer@EXAMPLE.com"
    name = "Jane Doe"
    user = User.objects.create_user(username, email=email, name=name, password=password)

    if username is not None:
        assert user.username == username
    else:
        assert isinstance(ulid.parse(user.username), ulid.ULID)
    assert user.email == "uSer@example.com"
    assert user.name == name
    assert user.get_full_name() == name
    assert user.is_staff is False
    assert user.is_superuser is False
    assert user.is_active is True
    if password is not None:
        assert user.check_password(password)


@pytest.mark.parametrize("username", [None, "user1"])
@pytest.mark.parametrize("password", [None, "pass"])
def test_create_superuser(username, password):
    """Test creating a user"""
    email = "uSer@EXAMPLE.com"
    name = "Jane Doe"
    user = User.objects.create_superuser(
        username, email=email, name=name, password=password
    )

    if username is not None:
        assert user.username == username
    else:
        assert isinstance(ulid.parse(user.username), ulid.ULID)
    assert user.email == "uSer@example.com"
    assert user.name == name
    assert user.get_full_name() == name
    assert user.is_staff is True
    assert user.is_superuser is True
    assert user.is_active is True
    if password is not None:
        assert user.check_password(password)


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
