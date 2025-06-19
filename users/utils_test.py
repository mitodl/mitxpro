"""User utils tests"""

import re
from unittest.mock import patch

import pytest

from users.factories import UserFactory
from users.utils import ensure_active_user, format_recipient


@patch("courseware.api.repair_faulty_edx_user", return_value=(None, None))
def test_ensure_active_user(mock_repair_faulty_edx_user, user):
    """
    Test that ensure_active_user activates and tries to repair courseware user record
    """
    user.is_active = False
    user.save()

    assert not user.is_active

    ensure_active_user(user)
    mock_repair_faulty_edx_user.assert_called_once_with(user)
    assert user.is_active


@pytest.mark.parametrize(
    "name, email",  # noqa: PT006
    [
        ["Mrs. Tammy Smith DDS", "HeSNMtNMfVdo@example.com"],  # noqa: PT007
        ["John Doe", "jd_123@example.com"],  # noqa: PT007
        ["Doe, Jane", "jd_456@example.com"],  # noqa: PT007
    ],
)
def test_format_recipient(name, email):
    """Verify that format_recipient correctly format's a user's name and email"""
    user = UserFactory.build(name=name, email=email)
    assert (
        re.fullmatch(rf"(\"?){user.name}(\"?)\s+<{user.email}>", format_recipient(user))
        is not None
    )
