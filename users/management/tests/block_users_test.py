"""block user test"""
import hashlib
import pytest
from django.contrib.auth import get_user_model
from django.test import TestCase

from users.factories import UserFactory
from users.management.commands import block_users
from users.models import BlockList

User = get_user_model()

COMMAND = block_users.Command()


class TestblockUsers(TestCase):
    """
    Tests block users management command.
    """

    def setUp(self):
        super().setUp()

    @pytest.mark.django_db
    def test_block_user_blocking_with_email(self):
        """test block_users command success with user email"""
        test_email = "test@email.com"

        user = UserFactory.create(email=test_email, is_active=True)
        email = user.email
        hashed_email = hashlib.md5(
            email.lower().encode("utf-8"), usedforsecurity=False
        ).hexdigest()
        assert BlockList.objects.all().count() == 0

        COMMAND.handle("block_users", users=[test_email], block_users=True)

        user.refresh_from_db()
        assert BlockList.objects.all().count() == 1
        assert BlockList.objects.filter(hashed_email=hashed_email).count() == 1

    @pytest.mark.django_db
    def test_multiple_success_blocking_user(self):
        """test block_users command blocking emails success with more than one user"""
        test_usernames = ["foo@test.com", "bar@test.com", "baz@test.com"]

        for username in test_usernames:
            user = UserFactory.create(username=username, is_active=True)
            assert BlockList.objects.all().count() == 0

        COMMAND.handle("block_users", users=test_usernames, block_users=True)
        assert BlockList.objects.all().count() == 3

    @pytest.mark.django_db
    def test_user_blocking_if_not_requested(self):
        """test block_users command exit if not user provided"""
        assert BlockList.objects.all().count() == 0
        with self.assertRaises(SystemExit):
            COMMAND.handle("block_users", users=[])

    @pytest.mark.django_db
    def test_user_blocking_with_invalid_email(self):
        """test block_users command system exit if not provided a valid email address"""
        test_email = "test.com"
        with self.assertRaises(SystemExit):
            COMMAND.handle("block_users", users=[test_email])
