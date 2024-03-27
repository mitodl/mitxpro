"""retire user test"""
import hashlib
import pytest
from django.contrib.auth import get_user_model
from social_django.models import UserSocialAuth

from users.factories import UserFactory, UserSocialAuthFactory
from users.management.commands import retire_users, unblock_users
from users.models import BlockList
from django.test import TestCase


User = get_user_model()


class TestUnblockUsers(TestCase):
    """
    Tests unblock users management command.
    """

    def setUp(self):
        super().setUp()
        self.RETIRE_USER_COMMAND = retire_users.Command()
        self.UNBLOCK_USER_COMMAND = unblock_users.Command()

    @pytest.mark.django_db
    def test_user_unblocking_with_email(self):
        """test unblock_users command success with user email"""
        test_email = "test@email.com"

        user = UserFactory.create(email=test_email, is_active=True)
        UserSocialAuthFactory.create(user=user, provider="edX")
        email = user.email
        hashed_email = hashlib.md5(
            email.lower().encode("utf-8"), usedforsecurity=False
        ).hexdigest()
        assert user.is_active is True
        assert "retired_email" not in user.email
        assert UserSocialAuth.objects.filter(user=user).count() == 1
        assert BlockList.objects.all().count() == 0

        self.RETIRE_USER_COMMAND.handle(
            "retire_users", users=[test_email], block_users=True
        )

        user.refresh_from_db()
        assert user.is_active is False
        assert "retired_email" in user.email
        assert UserSocialAuth.objects.filter(user=user).count() == 0
        assert BlockList.objects.all().count() == 1
        assert BlockList.objects.filter(hashed_email=hashed_email).count() == 1

        # Now we need to unblock the user from block list.
        self.UNBLOCK_USER_COMMAND.handle("unblock_users", users=[test_email])
        assert BlockList.objects.all().count() == 0
        assert BlockList.objects.filter(hashed_email=hashed_email).count() == 0

    @pytest.mark.django_db
    def test_multiple_success_unblocking_user(self):
        """test unblock_users command unblocking emails success with more than one user"""
        test_users = ["foo@email.com", "bar@email.com", "baz@email.com"]

        for email in test_users:
            user = UserFactory.create(email=email, is_active=True)
            UserSocialAuthFactory.create(user=user, provider="not_edx")

            assert user.is_active is True
            assert "retired_email" not in user.email
            assert UserSocialAuth.objects.filter(user=user).count() == 1
            assert BlockList.objects.all().count() == 0

        self.RETIRE_USER_COMMAND.handle(
            "retire_users", users=test_users, block_users=True
        )
        assert BlockList.objects.all().count() == 3

        # Now we need to unblock the user from block list.
        self.UNBLOCK_USER_COMMAND.handle("unblock_users", users=test_users)
        assert BlockList.objects.all().count() == 0

    @pytest.mark.django_db
    def test_user_unblocking_with_invalid_email(self):
        """test unblock_users command system exit if not provided a valid email address"""
        test_email = "test.com"
        with self.assertRaises(SystemExit):
            self.UNBLOCK_USER_COMMAND.handle("unblock_users", users=[test_email])

    @pytest.mark.django_db
    def test_user_unblocking_with_no_users(self):
        """test unblock_users command system exit if not any users provided"""
        with self.assertRaises(SystemExit):
            self.UNBLOCK_USER_COMMAND.handle("unblock_users", users=[])
