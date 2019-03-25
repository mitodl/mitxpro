"""Tests for user models"""
# pylint: disable=too-many-arguments, redefined-outer-name
import pytest
import ulid

from users.models import User

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    "create_func,exp_staff,exp_superuser",
    [
        [User.objects.create_user, False, False],
        [User.objects.create_superuser, True, True],
    ],
)
@pytest.mark.parametrize("username", [None, "user1"])
@pytest.mark.parametrize("password", [None, "pass"])
def test_create_user(
    create_func,
    exp_staff,
    exp_superuser,
    username,
    password,
    patch_create_edx_user_task,
):
    """Test creating a user"""
    email = "uSer@EXAMPLE.com"
    name = "Jane Doe"
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
    assert user.is_active is True
    if password is not None:
        assert user.check_password(password)
    patch_create_edx_user_task.delay.assert_called_once_with(user.id)


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
