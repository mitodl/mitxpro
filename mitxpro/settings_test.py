"""
Validate that our settings functions work
"""

import importlib
import sys
from unittest import mock

import semantic_version
from django.conf import settings
from django.core import mail
from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase
from mitol.common import envs, pytest_utils


REQUIRED_SETTINGS = {
    "MAILGUN_SENDER_DOMAIN": "mailgun.fake.domain",
    "MAILGUN_KEY": "fake_mailgun_key",
    "MITXPRO_BASE_URL": "http://localhost:8053",
}

# this is a test, but pylint thinks it ends up being unused
# hence we import the entire module and assign it here
test_app_json_modified = pytest_utils.test_app_json_modified


def cleanup_settings():
    """Cleanup settings after a test"""
    envs.env.reload()
    importlib.reload(sys.modules["mitol.digitalcredentials.settings"])
    importlib.reload(sys.modules["mitxpro.settings"])


class TestSettings(TestCase):
    """Validate that settings work as expected."""

    def patch_settings(self, values):
        """Patch the cached settings loaded by EnvParser"""
        with mock.patch.dict("os.environ", values, clear=True):
            envs.env.reload()
            settings_dict = self.reload_settings()
        return settings_dict

    def reload_settings(self):
        """
        Reload settings module with cleanup to restore it.

        Returns:
            dict: dictionary of the newly reloaded settings ``vars``
        """
        importlib.reload(sys.modules["mitxpro.settings"])
        # Restore settings to original settings after test
        self.addCleanup(cleanup_settings)
        return vars(sys.modules["mitxpro.settings"])

    def test_s3_settings(self):
        """Verify that we enable and configure S3 with a variable"""
        # Unset, we don't do S3
        settings_vars = self.patch_settings(
            {**REQUIRED_SETTINGS, "MITXPRO_USE_S3": "False"}
        )
        self.assertNotEqual(
            settings_vars.get("DEFAULT_FILE_STORAGE"),
            "storages.backends.s3boto3.S3Boto3Storage",
        )

        with self.assertRaises(ImproperlyConfigured):
            self.patch_settings({"MITXPRO_USE_S3": "True"})

        # Verify it all works with it enabled and configured 'properly'
        settings_vars = self.patch_settings(
            {
                **REQUIRED_SETTINGS,
                "MITXPRO_USE_S3": "True",
                "AWS_ACCESS_KEY_ID": "1",
                "AWS_SECRET_ACCESS_KEY": "2",
                "AWS_STORAGE_BUCKET_NAME": "3",
            }
        )
        self.assertEqual(
            settings_vars.get("DEFAULT_FILE_STORAGE"),
            "storages.backends.s3boto3.S3Boto3Storage",
        )

    def test_admin_settings(self):
        """Verify that we configure email with environment variable"""

        settings_vars = self.patch_settings(
            {**REQUIRED_SETTINGS, "MITXPRO_ADMIN_EMAIL": ""}
        )
        self.assertFalse(settings_vars.get("ADMINS", False))

        test_admin_email = "cuddle_bunnies@example.com"
        settings_vars = self.patch_settings(
            {**REQUIRED_SETTINGS, "MITXPRO_ADMIN_EMAIL": test_admin_email}
        )
        self.assertEqual((("Admins", test_admin_email),), settings_vars["ADMINS"])

        # Manually set ADMIN to our test setting and verify e-mail
        # goes where we expect
        settings.ADMINS = (("Admins", test_admin_email),)
        mail.mail_admins("Test", "message")
        self.assertIn(test_admin_email, mail.outbox[0].to)

    def test_csrf_trusted_origins(self):
        """Verify that we can configure CSRF_TRUSTED_ORIGINS with a var"""
        # Test the default
        settings_vars = self.patch_settings(REQUIRED_SETTINGS)
        self.assertEqual(settings_vars.get("CSRF_TRUSTED_ORIGINS"), [])

        # Verify the env var works
        settings_vars = self.patch_settings(
            {
                **REQUIRED_SETTINGS,
                "CSRF_TRUSTED_ORIGINS": "some.domain.com, some.other.domain.org",
            }
        )
        self.assertEqual(
            settings_vars.get("CSRF_TRUSTED_ORIGINS"),
            ["some.domain.com", "some.other.domain.org"],
        )

    def test_db_ssl_enable(self):
        """Verify that we can enable/disable database SSL with a var"""

        # Check default state is SSL on
        settings_vars = self.patch_settings(REQUIRED_SETTINGS)
        self.assertEqual(
            settings_vars["DATABASES"]["default"]["OPTIONS"], {"sslmode": "require"}
        )

        # Check enabling the setting explicitly
        settings_vars = self.patch_settings(
            {**REQUIRED_SETTINGS, "MITXPRO_DB_DISABLE_SSL": "True"}
        )
        self.assertEqual(settings_vars["DATABASES"]["default"]["OPTIONS"], {})

        # Disable it
        settings_vars = self.patch_settings(
            {**REQUIRED_SETTINGS, "MITXPRO_DB_DISABLE_SSL": "False"}
        )
        self.assertEqual(
            settings_vars["DATABASES"]["default"]["OPTIONS"], {"sslmode": "require"}
        )

    @staticmethod
    def test_semantic_version():
        """
        Verify that we have a semantic compatible version.
        """
        semantic_version.Version(settings.VERSION)

    def test_server_side_cursors_disabled(self):
        """DISABLE_SERVER_SIDE_CURSORS should be true by default"""
        settings_vars = self.patch_settings(REQUIRED_SETTINGS)
        assert (
            settings_vars["DEFAULT_DATABASE_CONFIG"]["DISABLE_SERVER_SIDE_CURSORS"]
            is True
        )

    def test_server_side_cursors_enabled(self):
        """DISABLE_SERVER_SIDE_CURSORS should be false if MITXPRO_DB_DISABLE_SS_CURSORS is false"""
        settings_vars = self.patch_settings(
            {**REQUIRED_SETTINGS, "MITXPRO_DB_DISABLE_SS_CURSORS": "False"}
        )
        assert (
            settings_vars["DEFAULT_DATABASE_CONFIG"]["DISABLE_SERVER_SIDE_CURSORS"]
            is False
        )
