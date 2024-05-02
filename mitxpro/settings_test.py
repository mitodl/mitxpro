"""
Validate that our settings functions work
"""

import sys
from types import SimpleNamespace

import pytest
import semantic_version
from django.core import mail
from django.core.exceptions import ImproperlyConfigured
from mitol.common import envs


# NOTE: this is temporarily inlined here until I can stabilize the test upstream in the library
def test_app_json_modified():
    """
    Pytest test that verifies app.json is up-to-date

    To use this, you should import this into a test file somewhere in your project:

    from mitol.common.pytest_utils import test_app_json_modified
    """
    import json
    import logging

    with open("app.json") as app_json_file:  # noqa: PTH123
        app_json = json.load(app_json_file)

    generated_app_json = envs.generate_app_json()

    if app_json != generated_app_json:
        logging.error(
            "Generated app.json does not match the app.json file. To fix this, run `./manage.py generate_app_json`"
        )

    # pytest will print the difference
    assert json.dumps(app_json, sort_keys=True, indent=2) == json.dumps(
        generated_app_json, sort_keys=True, indent=2
    )


@pytest.fixture(autouse=True)
def settings_sandbox(monkeypatch):
    """Cleanup settings after a test"""

    monkeypatch.delenv("MITXPRO_DB_DISABLE_SSL", raising=False)
    monkeypatch.setenv("DJANGO_SETTINGS_MODULE", "mitxpro.settings")
    monkeypatch.setenv("MAILGUN_SENDER_DOMAIN", "mailgun.fake.domain")
    monkeypatch.setenv("MAILGUN_KEY", "fake_mailgun_key")
    monkeypatch.setenv("MITXPRO_BASE_URL", "http://localhost:8053")

    def _get():
        return vars(sys.modules["mitxpro.settings"])

    def _patch(overrides):
        for key, value in overrides.items():
            monkeypatch.setenv(key, value)

        return _reload()

    def _reload():
        """
        Reload settings module with cleanup to restore it.

        Returns:
            dict: dictionary of the newly reloaded settings ``vars``
        """
        envs.env.reload()
        return _get()

    yield SimpleNamespace(
        patch=_patch,
        reload=_reload,
        get=_get,
    )

    _reload()


def test_s3_settings(settings_sandbox):
    """Verify that we enable and configure S3 with a variable"""
    # Unset, we don't do S3
    settings_vars = settings_sandbox.patch(
        {"MITXPRO_USE_S3": "False", "AWS_ACCESS_KEY_ID": ""}
    )

    assert settings_vars.get("DEFAULT_FILE_STORAGE") is None

    with pytest.raises(ImproperlyConfigured):
        settings_sandbox.patch({"MITXPRO_USE_S3": "True"})

    # Verify it all works with it enabled and configured 'properly'
    settings_vars = settings_sandbox.patch(
        {
            "MITXPRO_USE_S3": "True",
            "AWS_ACCESS_KEY_ID": "1",
            "AWS_SECRET_ACCESS_KEY": "2",
            "AWS_STORAGE_BUCKET_NAME": "3",
        }
    )
    assert (
        settings_vars.get("DEFAULT_FILE_STORAGE")
        == "storages.backends.s3boto3.S3Boto3Storage"
    )


def test_admin_settings(settings_sandbox, settings):
    """Verify that we configure email with environment variable"""

    settings_vars = settings_sandbox.patch({"MITXPRO_ADMIN_EMAIL": ""})
    assert settings_vars["ADMINS"] == ()

    test_admin_email = "cuddle_bunnies@example.com"
    settings_vars = settings_sandbox.patch({"MITXPRO_ADMIN_EMAIL": test_admin_email})
    assert (("Admins", test_admin_email),) == settings_vars["ADMINS"]

    # Manually set ADMIN to our test setting and verify e-mail
    # goes where we expect
    settings.ADMINS = (("Admins", test_admin_email),)
    mail.mail_admins("Test", "message")
    assert test_admin_email in mail.outbox[0].to


def test_csrf_trusted_origins(settings_sandbox):
    """Verify that we can configure CSRF_TRUSTED_ORIGINS with a var"""
    # Test the default
    settings_vars = settings_sandbox.get()
    assert settings_vars.get("CSRF_TRUSTED_ORIGINS") == []

    # Verify the env var works
    settings_vars = settings_sandbox.patch(
        {
            "CSRF_TRUSTED_ORIGINS": "some.domain.com, some.other.domain.org",
        }
    )
    assert settings_vars.get("CSRF_TRUSTED_ORIGINS") == [
        "some.domain.com",
        "some.other.domain.org",
    ]


def test_db_ssl_enable(monkeypatch, settings_sandbox):
    """Verify that we can enable/disable database SSL with a var"""
    # Check default state is SSL on
    settings_vars = settings_sandbox.reload()
    assert settings_vars["DATABASES"]["default"]["OPTIONS"] == {"sslmode": "require"}

    # Check enabling the setting explicitly
    settings_vars = settings_sandbox.patch({"MITXPRO_DB_DISABLE_SSL": "True"})
    assert settings_vars["DATABASES"]["default"]["OPTIONS"] == {}

    # Disable it
    settings_vars = settings_sandbox.patch({"MITXPRO_DB_DISABLE_SSL": "False"})
    assert settings_vars["DATABASES"]["default"]["OPTIONS"] == {"sslmode": "require"}


def test_semantic_version(settings):
    """
    Verify that we have a semantic compatible version.
    """
    semantic_version.Version(settings.VERSION)


def test_server_side_cursors_disabled(settings_sandbox):
    """DISABLE_SERVER_SIDE_CURSORS should be true by default"""
    settings_vars = settings_sandbox.get()
    assert (
        settings_vars["DEFAULT_DATABASE_CONFIG"]["DISABLE_SERVER_SIDE_CURSORS"] is True
    )


def test_server_side_cursors_enabled(settings_sandbox):
    """DISABLE_SERVER_SIDE_CURSORS should be false if MITXPRO_DB_DISABLE_SS_CURSORS is false"""
    settings_vars = settings_sandbox.patch({"MITXPRO_DB_DISABLE_SS_CURSORS": "False"})
    assert (
        settings_vars["DEFAULT_DATABASE_CONFIG"]["DISABLE_SERVER_SIDE_CURSORS"] is False
    )
