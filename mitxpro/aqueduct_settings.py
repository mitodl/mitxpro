"""Typed, validated Django settings for mitxpro, powered by django-aqueduct.

This module is the pydantic counterpart of ``mitxpro/settings.py``. It is
**not** used by default: the app keeps ``mitxpro.settings`` (the classic
``EnvParser``-based module) as its settings module everywhere it runs today.
This file only takes effect when something explicitly sets
``DJANGO_SETTINGS_MODULE=mitxpro.settings_aqueduct``.

The generator scaffold (``manage.py generate_aqueduct_settings --modules
mitxpro.settings --include-envparser``) was used as a starting point, then
hand refined:

* Every ``get_string``/``get_bool``/``get_int``/``get_delimited_list`` call in
  ``mitxpro/settings.py`` (and the mitol modules it imports via
  ``import_settings_modules``) is represented as a field here, using the
  *environment variable name* as the field name whenever it differs from the
  Django setting name mitxpro.settings ultimately exposes (see the "derived
  aliases" validator below).
* Values mitxpro.settings computes from other settings (``DATABASES``,
  ``CACHES``, ``INSTALLED_APPS``/``MIDDLEWARE`` conditionals,
  ``CELERY_BEAT_SCHEDULE``, ``FEATURES``, etc.) are modelled as
  ``model_validator`` methods instead of baked-in literal defaults, so they
  stay correct regardless of which environment variables are actually set.

Note: this pass intentionally does **not** add a Vault-backed
``DevAqueductSettings`` variant. See ``docs/aqueduct.md`` for why.
"""

from __future__ import annotations

import logging
import os
import pathlib
import platform
from datetime import timedelta
from typing import Any
from urllib.parse import urljoin, urlparse
from zoneinfo import ZoneInfo

import dj_database_url
from celery.schedules import crontab
from django.core.exceptions import ImproperlyConfigured
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from redbeat import RedBeatScheduler

from mitxpro.celery_utils import OffsettingSchedule

VERSION = "0.195.1"

# mitxpro/settings.py computes BASE_DIR as the parent of the directory that
# contains it. This module lives in the same directory, so the same
# computation yields the same project root.
BASE_DIR = str(pathlib.Path(__file__).resolve().parent.parent)


class AqueductSettings(BaseSettings):
    """Typed Django settings model mirroring ``mitxpro/settings.py``.

    Populated from environment variables by pydantic-settings' default
    behavior (field name, case-insensitive, matches env var name). Fields
    below use the raw environment variable name whenever it differs from the
    Django setting name (e.g. ``MITXPRO_BASE_URL`` vs. ``SITE_BASE_URL``);
    the "derived aliases" validator copies the resolved value onto the
    Django-facing attribute name.
    """

    model_config = SettingsConfigDict(env_prefix="", extra="allow")

    # ===== core / environment =====
    MITXPRO_ENVIRONMENT: str = Field(
        default="dev",
        description="The execution environment that the app is in (e.g. dev, staging, prod)",
    )
    HEROKU_APP_NAME: str | None = Field(
        default=None, description="The name of the review app"
    )
    SENTRY_DSN: str = Field(
        default="", description="The connection settings for Sentry"
    )
    SENTRY_LOG_LEVEL: str = Field(
        default="ERROR", description="The log level for Sentry"
    )

    # ===== site / security =====
    MITXPRO_BASE_URL: str = Field(
        description="Base url for the application in the format PROTOCOL://HOSTNAME[:PORT]"
    )
    SECRET_KEY: str = Field(description="Django secret key.")
    ALLOWED_HOSTS: list[str] = Field(default_factory=lambda: ["*"])
    DEBUG: bool = Field(
        default=False,
        description="Set to True to enable DEBUG mode. Don't turn on in production.",
    )
    CSRF_TRUSTED_ORIGINS: list[str] = Field(
        default_factory=list,
        description="Comma separated string of trusted domains that should be CSRF exempt",
    )
    MITXPRO_SECURE_SSL_REDIRECT: bool = Field(
        default=True, description="Application-level SSL redirect setting."
    )
    MITXPRO_SECURE_SSL_HOST: str | None = Field(
        default=None,
        description="Hostame to redirect non-secure requests to. Overrides value from HOST header.",
    )
    MITXPRO_SITE_ID: int = Field(
        default=1, description="The default site id for django sites framework"
    )
    HOST_IP: str = Field(default="127.0.0.1", description="This server's host IP")

    # ===== database =====
    DATABASE_URL: str = Field(
        default=f"sqlite:///{BASE_DIR}/db.sqlite3",
        description="The connection url to the Postgres database",
    )
    MITXPRO_DB_CONN_MAX_AGE: int = Field(
        default=0, description="Maximum age of connection to Postgres in seconds"
    )
    MITXPRO_DB_DISABLE_SS_CURSORS: bool = Field(
        default=True, description="Disables Postgres server side cursors"
    )
    MITXPRO_DB_DISABLE_SSL: bool = Field(
        default=False, description="Disables SSL to postgres if set to True"
    )

    # ===== django-robots =====
    ROBOTS_CACHE_TIMEOUT: int = Field(
        default=60 * 60 * 24,
        description="How long the robots.txt file should be cached",
    )

    # ===== social auth =====
    LOGOUT_REDIRECT_URL: str = Field(
        default="/",
        description="Url to redirect to after logout, typically Open edX's own logout url",
    )
    AUTH_CHANGE_EMAIL_TTL_IN_MINUTES: int = Field(
        default=60 * 24,
        description="Expiry time for a change email request, default is 1440 minutes(1 day)",
    )

    # ===== static / media / S3 =====
    CLOUDFRONT_DIST: str | None = Field(
        default=None,
        description="The Cloundfront distribution to use for static assets",
    )
    MEDIA_ROOT: str = Field(
        default="/var/media/",
        description="The root directory for locally stored media. Typically not used.",
    )
    MITXPRO_USE_S3: bool = Field(
        default=False, description="Use S3 for storage backend (required on Heroku)"
    )
    AWS_ACCESS_KEY_ID: str | None = Field(
        default=None, description="AWS Access Key for S3 storage."
    )
    AWS_SECRET_ACCESS_KEY: str | None = Field(
        default=None, description="AWS Secret Key for S3 storage."
    )
    AWS_STORAGE_BUCKET_NAME: str | None = Field(
        default=None, description="S3 Bucket name."
    )
    AWS_QUERYSTRING_AUTH: bool = Field(
        default=False, description="Enables querystring auth for S3 urls"
    )

    # ===== email =====
    MITXPRO_EMAIL_BACKEND: str = Field(
        default="django.core.mail.backends.smtp.EmailBackend",
        description=(
            "The default email backend to use for outgoing email. This is used in "
            "some places by django itself. See `NOTIFICATION_EMAIL_BACKEND` for the "
            "backend used for most application emails."
        ),
    )
    MITXPRO_EMAIL_HOST: str = Field(
        default="localhost", description="Outgoing e-mail hostname"
    )
    MITXPRO_EMAIL_PORT: int = Field(default=25, description="Outgoing e-mail port")
    MITXPRO_EMAIL_USER: str = Field(
        default="", description="Outgoing e-mail auth username"
    )
    MITXPRO_EMAIL_PASSWORD: str = Field(
        default="", description="Outgoing e-mail auth password"
    )
    MITXPRO_EMAIL_TLS: bool = Field(
        default=False, description="Outgoing e-mail TLS setting"
    )
    MITXPRO_REPLY_TO_ADDRESS: str = Field(
        default="webmaster@localhost",
        description="E-mail to use for reply-to address of emails",
    )
    MITXPRO_FROM_EMAIL: str = Field(
        default="webmaster@localhost", description="E-mail to use for the from field"
    )
    MAILGUN_SENDER_DOMAIN: str = Field(
        description="The domain to send mailgun email through"
    )
    MAILGUN_KEY: str = Field(
        description="The token for authenticating against the Mailgun API"
    )
    MAILGUN_BATCH_CHUNK_SIZE: int = Field(
        default=1000, description="Maximum number of emails to send in a batch"
    )
    MAILGUN_RECIPIENT_OVERRIDE: str | None = Field(
        default=None,
        description="Override the recipient for outgoing email, development only",
    )
    MAILGUN_FROM_EMAIL: str = Field(
        default="no-reply@localhost", description="Email which mail comes from"
    )
    MITXPRO_SUPPORT_EMAIL: str | None = Field(
        default=None,
        description="Email address listed for customer support",
    )
    MITXPRO_NOTIFICATION_EMAIL_BACKEND: str = Field(
        default="anymail.backends.mailgun.EmailBackend",
        description="The email backend to use for application emails",
    )
    MITXPRO_ADMIN_EMAIL: str = Field(
        default="", description="E-mail to send 500 reports to."
    )

    # ===== logging =====
    MITXPRO_LOG_LEVEL: str = Field(default="INFO", description="The log level default")
    DJANGO_LOG_LEVEL: str = Field(
        default="INFO", description="The log level for django"
    )

    # ===== marketing / recaptcha =====
    GTM_TRACKING_ID: str = Field(
        default="", description="Google Tag Manager container ID"
    )
    GA_TRACKING_ID: str = Field(default="", description="Google analytics tracking ID")
    REACT_GA_DEBUG: bool = Field(
        default=False, description="Enable debug for react-ga, development only"
    )
    RECAPTCHA_SITE_KEY: str = Field(default="", description="The ReCaptcha site key")
    RECAPTCHA_SECRET_KEY: str = Field(
        default="", description="The ReCaptcha secret key"
    )
    USE_X_FORWARDED_HOST: bool = Field(
        default=False,
        description="Set HOST header to original domain accessed by user",
    )
    SITE_NAME: str = Field(
        default="MIT xPRO", description="Name of the site. e.g MIT xPRO"
    )

    # ===== features =====
    # Populated by `_scan_features` below from every `FEATURE_*` env var.
    FEATURES: dict[str, bool] = Field(default_factory=dict)

    # ===== certificates =====
    CERTIFICATE_CREATION_DELAY_IN_HOURS: int = Field(
        default=48,
        description="The number of hours to delay automated certificate creation after a course run ends.",
    )

    # ===== redis =====
    REDISCLOUD_URL: str | None = Field(
        default=None, description="RedisCloud connection url"
    )
    REDIS_URL: str | None = Field(
        default=None, description="Redis URL for non-production use"
    )

    # ===== celery =====
    CELERY_BROKER_URL: str | None = Field(
        default=None, description="Where celery should get tasks, default is Redis URL"
    )
    CELERY_RESULT_BACKEND: str | None = Field(
        default=None,
        description="Where celery should put task results, default is Redis URL",
    )
    CELERY_REDBEAT_REDIS_URL: str | None = Field(default=None)
    CELERY_TASK_ALWAYS_EAGER: bool = Field(
        default=False,
        description="Enables eager execution of celery tasks, development only",
    )
    CELERY_TASK_EAGER_PROPAGATES: bool = Field(
        default=True, description="Early executed tasks propagate exceptions"
    )
    CELERY_TASK_SERIALIZER: str = Field(default="json")
    CELERY_RESULT_SERIALIZER: str = Field(default="json")
    CELERY_ACCEPT_CONTENT: list[str] = Field(default_factory=lambda: ["json"])
    CELERY_TIMEZONE: str = Field(default="UTC")
    CELERY_TASK_TRACK_STARTED: bool = Field(default=True)
    CELERY_TASK_SEND_SENT_EVENT: bool = Field(default=True)
    # Populated by `_build_celery_beat_schedule` below (embeds crontab /
    # OffsettingSchedule objects, which are not JSON-serialisable).
    CELERY_BEAT_SCHEDULE: dict[str, Any] = Field(default_factory=dict)
    CELERY_BEAT_SCHEDULER: Any = Field(default_factory=lambda: RedBeatScheduler)

    CRON_COURSE_CERTIFICATES_HOURS: int | str = Field(
        default=0,
        description="'hours' value for the 'generate-course-certificate' scheduled task (defaults to midnight)",
    )
    CRON_COURSE_CERTIFICATES_DAYS: str | None = Field(
        default=None,
        description="'day_of_week' value for 'generate-course-certificate' scheduled task (default will run once a day).",
    )
    CRON_COURSERUN_SYNC_HOURS: int | str = Field(
        default=0,
        description="'hours' value for the 'sync-courseruns-data' scheduled task (defaults to midnight)",
    )
    CRON_COURSERUN_SYNC_DAYS: str | None = Field(
        default=None,
        description="'day_of_week' value for 'sync-courseruns-data' scheduled task (default will run once a day).",
    )
    CRON_EXTERNAL_COURSERUN_SYNC_HOURS: int | str = Field(
        default="0",
        description="'hours' value for the 'sync-external-course-runs' scheduled task (defaults to midnight)",
    )
    CRON_EXTERNAL_COURSERUN_SYNC_DAYS: str | None = Field(
        default=None,
        description="'day_of_week' value for 'sync-external-course-runs' scheduled task (default will run once a day).",
    )
    CRON_BASKET_DELETE_HOURS: int | str = Field(
        default=0,
        description="'hours' value for the 'delete-expired-baskets' scheduled task (defaults to midnight)",
    )
    CRON_BASKET_DELETE_DAYS: str = Field(
        default="*",
        description="'days' value for the 'delete-expired-baskets' scheduled task (defaults to everyday)",
    )
    BASKET_EXPIRY_DAYS: int = Field(
        default=15, description="Expiry life span of a basket in days"
    )

    RETRY_FAILED_EDX_ENROLLMENT_FREQUENCY: int = Field(
        default=60 * 30,
        description="How many seconds between retrying failed edX enrollments",
    )
    REPAIR_COURSEWARE_USERS_FREQUENCY: int = Field(
        default=60 * 30,
        description="How many seconds between repairing courseware records for faulty users",
    )
    # Populated by `_build_derived_aliases`: int(REPAIR_COURSEWARE_USERS_FREQUENCY / 2)
    REPAIR_COURSEWARE_USERS_OFFSET: int = Field(default=0)

    DRIVE_WEBHOOK_EXPIRATION_MINUTES: int = Field(
        default=60 * 24,
        description=(
            "The number of minutes after creation that a webhook (push notification) for a Drive "
            "file will expire (Google does not accept an expiration beyond 24 hours, and if the "
            "expiration is not provided via API, it defaults to 1 hour)."
        ),
    )
    DRIVE_WEBHOOK_RENEWAL_PERIOD_MINUTES: int = Field(
        default=60 * 3,
        description=(
            "The maximum time difference (in minutes) from the present time to a webhook expiration "
            "date to consider a webhook 'fresh', i.e.: not in need of renewal. If the time difference "
            "is less than this value, the webhook should be renewed."
        ),
    )
    DRIVE_WEBHOOK_ASSIGNMENT_WAIT: int = Field(
        default=60 * 5,
        description=(
            "The number of seconds to wait to process a coupon assignment sheet after we receive "
            "a webhook request from that sheet. The task to process the sheet is scheduled this many "
            "seconds in the future."
        ),
    )
    DRIVE_WEBHOOK_ASSIGNMENT_MAX_AGE_DAYS: int = Field(
        default=30,
        description=(
            "The number of days from the last update that a coupon assignment sheet should still be "
            "considered 'fresh', i.e.: should still be monitored for changes via webhook/file watch."
        ),
    )
    SHEETS_MONITORING_FREQUENCY: int = Field(
        default=60 * 60 * 2,
        description="The frequency that the Drive folder should be checked for bulk coupon Sheets that need processing",
    )
    SHEETS_TASK_OFFSET: int = Field(
        default=60 * 5,
        description="How many seconds to wait in between executing different Sheets tasks in series",
    )

    # ===== wagtail =====
    WAGTAIL_CACHE_BACKEND: str = Field(
        default="django_redis.cache.RedisCache",
        description="The caching backend to be used for Wagtail image renditions",
    )
    WAGTAIL_CACHE_URL: str | None = Field(
        default=None, description="URL for Wagtail image renditions cache"
    )
    WAGTAIL_CACHE_MAX_ENTRIES: int = Field(
        default=200,
        description="The maximum number of cache entries for Wagtail images",
    )
    BLOG_CACHE_TIMEOUT: int = Field(
        default=60 * 60 * 24, description="How long the blog should be cached"
    )

    # ===== oauth2 =====
    OAUTH2_PROVIDER_ALLOWED_REDIRECT_URI_SCHEMES: list[str] = Field(
        default_factory=lambda: ["http", "https"],
        description="List of schemes allowed for oauth2 redirect URIs",
    )
    REFRESH_TOKEN_EXPIRE_SECONDS: int = Field(
        default=60 * 60 * 24 * 30,
        description="Number of seconds until a refresh token expires",
    )

    # ===== mitol-django-mail / mitol-django-common =====
    MITOL_MAIL_ENABLE_EMAIL_DEBUGGER: bool = Field(
        default=False,
        description="Enable the mitol-mail email debugger",
    )

    # ===== mitol-django-authentication (djoser) =====
    MITOL_AUTHENTICATION_REPLY_TO_ADDRESS: str = Field(
        default="webmaster@localhost",
        description="E-mail to use for reply-to address of emails",
    )

    # ===== Open edX =====
    OPENEDX_OAUTH_PROVIDER: str = Field(
        default="ol-oauth2", description="Social auth oauth provider backend name"
    )
    OPENEDX_SOCIAL_LOGIN_PATH: str = Field(
        default="/auth/login/ol-oauth2/?auth_entry=login",
        description="Open edX social auth login url",
    )
    OPENEDX_OAUTH_APP_NAME: str = Field(
        default="edx-oauth-app",
        description="The 'name' value for the Open edX OAuth Application",
    )
    OPENEDX_API_BASE_URL: str = Field(
        default="http://local.openedx.io:8000",
        description="The base URL for the Open edX API",
    )
    OPENEDX_BASE_REDIRECT_URL: str | None = Field(
        default=None,
        description="The base redirect URL for an OAuth Application for the Open edX API",
    )
    OPENEDX_TOKEN_EXPIRES_HOURS: int = Field(
        default=1000,
        description="The number of hours until an access token for the Open edX API expires",
    )
    OPENEDX_API_CLIENT_ID: str = Field(
        description="The OAuth2 client id to connect to Open edX with"
    )
    OPENEDX_API_CLIENT_SECRET: str = Field(
        description="The OAuth2 client secret to connect to Open edX with"
    )
    MITXPRO_REGISTRATION_ACCESS_TOKEN: str | None = Field(
        default=None,
        description="Access token to secure Open edX registration API with",
    )
    OPENEDX_SERVICE_WORKER_API_TOKEN: str | None = Field(
        default=None,
        description="Active access token with staff level permissions to use with OpenEdX API client for service tasks",
    )
    OPENEDX_SERVICE_WORKER_USERNAME: str | None = Field(
        default=None,
        description="Username of the user whose token has been set in OPENEDX_SERVICE_WORKER_API_TOKEN",
    )
    EDX_API_CLIENT_TIMEOUT: int = Field(
        default=60,
        description="Timeout (in seconds) for requests made via the edX API client",
    )
    EXTERNAL_COURSE_SYNC_API_KEY: str = Field(
        description="The API Key for external course sync API"
    )
    EXTERNAL_COURSE_SYNC_API_BASE_URL: str = Field(
        default="https://mit-xpro.emeritus-analytics.io/",
        description="Base API URL for external course sync API",
    )
    EXTERNAL_COURSE_SYNC_API_REQUEST_TIMEOUT: int = Field(
        default=60,
        description="API request timeout for external course sync APIs in seconds",
    )
    EXTERNAL_COURSE_SYNC_EMAIL_RECIPIENTS: list[str] = Field(
        default_factory=list,
        description="Comma-separated list of email addresses to receive notifications about external data syncs",
    )

    # ===== Cybersource =====
    CYBERSOURCE_ACCESS_KEY: str | None = Field(
        default=None, description="CyberSource Access Key"
    )
    CYBERSOURCE_SECURITY_KEY: str | None = Field(
        default=None, description="CyberSource API key"
    )
    CYBERSOURCE_SECURE_ACCEPTANCE_URL: str | None = Field(
        default=None, description="CyberSource API endpoint"
    )
    CYBERSOURCE_PROFILE_ID: str | None = Field(
        default=None, description="CyberSource Profile ID"
    )
    CYBERSOURCE_WSDL_URL: str | None = Field(
        default=None, description="The URL to the cybersource WSDL"
    )
    CYBERSOURCE_MERCHANT_ID: str | None = Field(
        default=None, description="The cybersource merchant id"
    )
    CYBERSOURCE_TRANSACTION_KEY: str | None = Field(
        default=None, description="The cybersource transaction key"
    )
    CYBERSOURCE_INQUIRY_LOG_NACL_ENCRYPTION_KEY: str | None = Field(
        default=None,
        description=(
            "The public key to encrypt export results with for our own security purposes. "
            "Should be a base64 encoded NaCl public key."
        ),
    )
    CYBERSOURCE_EXPORT_SERVICE_ADDRESS_OPERATOR: str = Field(
        default="AND",
        description=(
            "Whether just the name or the name and address should be used in exports "
            "verification. Refer to Cybersource docs."
        ),
    )
    CYBERSOURCE_EXPORT_SERVICE_ADDRESS_WEIGHT: str = Field(
        default="high",
        description=(
            "The weight of the address in determining whether a user passes exports "
            "checks. Refer to Cybersource docs."
        ),
    )
    CYBERSOURCE_EXPORT_SERVICE_NAME_WEIGHT: str = Field(
        default="high",
        description=(
            "The weight of the name in determining whether a user passes exports checks. "
            "Refer to Cybersource docs."
        ),
    )
    CYBERSOURCE_EXPORT_SERVICE_SANCTIONS_LISTS: str | None = Field(
        default=None,
        description="Additional sanctions lists to validate for exports. Refer to Cybersource docs.",
    )

    # ===== Vouchers =====
    VOUCHER_DOMESTIC_EMPLOYEE_KEY: str = Field(
        default="UNIQUE02", description="Employee key for domestic vouchers"
    )
    VOUCHER_DOMESTIC_EMPLOYEE_ID_KEY: str = Field(
        default="UNIQUE03",
        description="Voucher employee key ID for domestic vouchers",
    )
    VOUCHER_DOMESTIC_KEY: str = Field(
        default="UNIQUE04", description="Voucher key for domestic vouchers"
    )
    VOUCHER_DOMESTIC_COURSE_KEY: str = Field(
        default="UNIQUE05", description="Course key for domestic vouchers"
    )
    VOUCHER_DOMESTIC_CREDITS_KEY: str = Field(
        default="UNIQUE06", description="Credits key for domestic vouchers"
    )
    VOUCHER_DOMESTIC_DATES_KEY: str = Field(
        default="UNIQUE07", description="Dates key for domestic vouchers"
    )
    VOUCHER_DOMESTIC_AMOUNT_KEY: str = Field(
        default="UNIQUE08", description="Amount key for domestic vouchers"
    )
    VOUCHER_INTERNATIONAL_EMPLOYEE_KEY: str = Field(
        default="UNIQUE09", description="Employee key for international vouchers"
    )
    VOUCHER_INTERNATIONAL_EMPLOYEE_ID_KEY: str = Field(
        default="UNIQUE13",
        description="Voucher employee key ID for international vouchers",
    )
    VOUCHER_INTERNATIONAL_DATES_KEY: str = Field(
        default="UNIQUE15", description="Dates key for international vouchers"
    )
    VOUCHER_INTERNATIONAL_COURSE_NAME_KEY: str = Field(
        default="UNIQUE16", description="Course name key for international vouchers"
    )
    VOUCHER_INTERNATIONAL_COURSE_NUMBER_KEY: str = Field(
        default="UNIQUE17",
        description="Course number key for international vouchers",
    )
    VOUCHER_COMPANY_ID: int = Field(default=1, description="Company ID for vouchers")

    # ===== Hubspot =====
    MITOL_HUBSPOT_API_PRIVATE_TOKEN: str | None = Field(
        default=None, description="Hubspot private token to authenticate with API"
    )
    MITOL_HUBSPOT_API_RETRIES: int = Field(
        default=3,
        description="Number of times to retry a failed hubspot API request",
    )
    MITOL_HUBSPOT_API_ID_PREFIX: str = Field(
        default="XPRO",
        description="The prefix to use for hubspot unique_app_id field values",
    )
    HUBSPOT_PIPELINE_ID: str = Field(
        default="default", description="Hubspot ID for the ecommerce pipeline"
    )
    HUBSPOT_MAX_CONCURRENT_TASKS: int = Field(
        default=4, description="Max number of concurrent Hubspot tasks to run"
    )
    HUBSPOT_TASK_DELAY: int = Field(
        default=1000,
        description="Number of milliseconds to wait between consecutive Hubspot calls",
    )
    HUBSPOT_NEW_COURSES_FORM_GUID: str = Field(
        default="",
        description="Form guid over hub spot for new courses email subscription form.",
    )
    HUBSPOT_FOOTER_FORM_GUID: str = Field(
        default="", description="Form guid over hub spot for footer block."
    )
    HUBSPOT_PORTAL_ID: str = Field(default="", description="Hub spot portal id.")
    HUBSPOT_CREATE_USER_FORM_ID: str | None = Field(
        default=None, description="Form ID for Hubspot Forms API"
    )
    HUBSPOT_ENTERPRISE_PAGE_FORM_ID: str | None = Field(
        default=None, description="Form ID for Hubspot for Enterprise Page"
    )

    # ===== Sheets =====
    DRIVE_SERVICE_ACCOUNT_CREDS: str | None = Field(
        default=None,
        description="The contents of the Service Account credentials JSON to use for Google API auth",
    )
    DRIVE_CLIENT_ID: str | None = Field(
        default=None, description="Client ID from Google API credentials"
    )
    DRIVE_CLIENT_SECRET: str | None = Field(
        default=None, description="Client secret from Google API credentials"
    )
    DRIVE_API_PROJECT_ID: str | None = Field(
        default=None,
        description="ID for the Google API project where the credentials were created",
    )
    DRIVE_WEBHOOK_CHANNEL_ID: str = Field(
        default="mitxpro-sheets-app",
        description="Channel ID to use for requests to get push notifications for file changes",
    )
    DRIVE_SHARED_ID: str | None = Field(
        default=None,
        description="ID of the Shared Drive (a.k.a. Team Drive). This is equal to the top-level folder ID.",
    )
    DRIVE_OUTPUT_FOLDER_ID: str | None = Field(
        default=None,
        description="ID of the Drive folder where newly created Sheets should be kept",
    )
    COUPON_REQUEST_SHEET_ID: str | None = Field(
        default=None,
        description="ID of the Google Sheet that contains requests for coupons",
    )
    ENROLLMENT_CHANGE_SHEET_ID: str | None = Field(
        default=None,
        description=(
            "ID of the Google Sheet that contains the enrollment change request "
            "worksheets (refunds, transfers, etc)"
        ),
    )
    REFUND_REQUEST_WORKSHEET_ID: str = Field(
        default="0",
        description=(
            "ID of the worksheet within the enrollment change request spreadsheet "
            "that contains enrollment refund requests"
        ),
    )
    DEFERRAL_REQUEST_WORKSHEET_ID: str | None = Field(
        default=None,
        description=(
            "ID of the worksheet within the enrollment change request spreadsheet that "
            "contains enrollment deferral requests"
        ),
    )
    GOOGLE_DOMAIN_VERIFICATION_TAG_VALUE: str | None = Field(
        default=None,
        description=(
            "The value of the meta tag used by Google to verify the owner of a domain "
            "(used for enabling push notifications)"
        ),
    )
    SHEETS_ADMIN_EMAILS: list[str] = Field(
        default_factory=list,
        description=(
            "Comma-separated list of emails for users that should be added as an "
            "editor for all newly created Sheets"
        ),
    )
    SHEETS_DATE_FORMAT: str = Field(
        default="%m/%d/%Y %H:%M:%S",
        description="Python strptime format for datetime columns in enrollment management spreadsheets",
    )
    SHEETS_DATE_ONLY_FORMAT: str = Field(
        default="%m/%d/%Y",
        description="Python strptime format for date columns (no time) in enrollment management spreadsheets",
    )
    # Raw env value; `_build_derived_aliases` converts it to a ZoneInfo and
    # stores it on `SHEETS_DATE_TIMEZONE` (mitxpro.settings does the same
    # thing: `SHEETS_DATE_TIMEZONE = ZoneInfo(_sheets_date_timezone)`).
    SHEETS_DATE_TIMEZONE_NAME: str = Field(
        default="UTC",
        validation_alias="SHEETS_DATE_TIMEZONE",
        description=(
            "The name of the timezone that should be assumed for date/time values in "
            "spreadsheets. Choose from a value in the TZ database "
            "(https://en.wikipedia.org/wiki/List_of_tz_database_time_zones)."
        ),
    )
    SHEETS_DATE_TIMEZONE: Any = Field(default=None)
    SHEETS_REFUND_FIRST_ROW: int = Field(
        default=4,
        description=(
            "The first row (as it appears in the spreadsheet) of data that our scripts "
            "should consider processing in the refund request spreadsheet"
        ),
    )
    SHEETS_DEFERRAL_FIRST_ROW: int = Field(
        default=5,
        description=(
            "The first row (as it appears in the spreadsheet) of data that our scripts "
            "should consider processing in the deferral request spreadsheet"
        ),
    )
    SHEETS_REFUND_PROCESSOR_COL: int = Field(
        default=11,
        description=(
            "The zero-based index of the enrollment change sheet column that contains "
            "the user that processed the row"
        ),
    )
    SHEETS_REFUND_COMPLETED_DATE_COL: int = Field(
        default=12,
        description=(
            "The zero-based index of the enrollment change sheet column that contains "
            "the row completion date"
        ),
    )
    SHEETS_REFUND_ERROR_COL: int = Field(
        default=13,
        description=(
            "The zero-based index of the enrollment change sheet column that contains "
            "row processing error messages"
        ),
    )
    SHEETS_REFUND_SKIP_ROW_COL: int = Field(
        default=14,
        description=(
            "The zero-based index of the enrollment change sheet column that indicates "
            "whether the row should be skipped"
        ),
    )

    # ===== Digital Credentials =====
    DIGITAL_CREDENTIALS_DEEP_LINK_URL: str | None = Field(
        default=None,
        description="URL at which to deep link the learner to for the digital credentials wallet",
    )
    DIGITAL_CREDENTIALS_ISSUER_ID: str | None = Field(
        default=None, description="Issuer identifier for digital credentials"
    )
    DIGITAL_CREDENTIALS_VERIFICATION_METHOD: str | None = Field(
        default=None, description="Verification method for digital credentials"
    )
    DIGITAL_CREDENTIALS_SUPPORTED_RUNS: list[str] = Field(
        default_factory=list,
        description="Comma separated string of course/program runs/Ids that support digital credentials",
    )
    MITOL_DIGITAL_CREDENTIALS_VERIFY_SERVICE_BASE_URL: str | None = Field(
        default=None,
        description="Base URL for sing-and-verify service to call for digital credentials",
    )
    MITOL_DIGITAL_CREDENTIALS_HMAC_SECRET: str | None = Field(
        default=None,
        description="HMAC secret to sign digital credentials requests with",
    )
    MITOL_DIGITAL_CREDENTIALS_DEEP_LINK_URL: str | None = Field(
        default=None,
        description="URL at which to deep link the learner to for the digital credentials wallet",
    )
    MITOL_DIGITAL_CREDENTIALS_AUTH_TYPE: str | None = Field(
        default=None,
        description="Auth type that is passed to the digital credentials wallet app",
    )

    # ===== webpack (mitol.common.settings.webpack) =====
    WEBPACK_DEV_SERVER_HOST: str = Field(
        default="", description="The webpack dev server hostname, development only"
    )
    WEBPACK_DEV_SERVER_PORT: int | None = Field(
        default=None, description="The webpack dev server port, development only"
    )
    WEBPACK_DISABLE_LOADER_STATS: bool = Field(
        default=False,
        description="Disables the webpack loader, development environment only.",
    )
    WEBPACK_USE_DEV_SERVER: bool = Field(
        default=False, description="Enables the webpack devserver, development only"
    )

    # ===== PostHog (mitol.olposthog.settings.olposthog) =====
    POSTHOG_ENABLED: bool = Field(
        default=False, description="Whether to enable Posthog feature flags"
    )
    POSTHOG_PROJECT_API_KEY: str = Field(
        default="",
        description="Public API key (usually, phc_...) to communicate with PostHog",
    )
    POSTHOG_PERSONAL_API_KEY: str = Field(
        default="",
        description=(
            "Personal API key (usually phx_...) or Feature Flag API key (usually phs...) "
            "for PostHog local flag evaluation. When set, flags are evaluated locally "
            "without per-request HTTP calls."
        ),
    )
    POSTHOG_API_HOST: str = Field(
        default="https://us.posthog.com", description="Host URL for the PostHog API"
    )
    POSTHOG_FEATURE_FLAG_REQUEST_TIMEOUT_MS: int = Field(
        default=3000, description="Timeout(MS) for PostHog feature flag requests."
    )
    POSTHOG_MAX_RETRIES: int = Field(
        default=3,
        description="Numbers of time requests to PostHog should be retried after failing.",
    )
    POSTHOG_POLL_INTERVAL: int = Field(
        default=300,
        description=(
            "Seconds between PostHog flag config polling. Relevant when "
            "POSTHOG_PERSONAL_API_KEY is set for local evaluation."
        ),
    )
    POSTHOG_CIRCUIT_BREAKER_COOLDOWN_SECONDS: int = Field(
        default=60,
        description="Seconds to wait before retrying PostHog after a failed request.",
    )
    POSTHOG_CIRCUIT_BREAKER_TRIP_THRESHOLD_SECONDS: int = Field(
        default=6,
        description="Seconds a PostHog request can take before the circuit breaker trips.",
    )

    # ===== ecommerce / misc feature toggles =====
    ECOMMERCE_FORCE_PROFILE_COUNTRY: bool = Field(
        default=False,
        description="Force the country determination to be done with the user profile only",
    )
    CANONICAL_HOSTNAME_REDIRECT_ENABLED: bool = Field(
        default=False,
        description=(
            "Whether to enable redirecting to the canonical hostname defined in "
            "SITE_BASE_URL when a request comes in with a different hostname"
        ),
    )

    # =====================================================================
    # Static Django settings (not sourced from the environment). Included
    # here 1:1 with mitxpro/settings.py for completeness/parity.
    # =====================================================================
    AUTH_USER_MODEL: str = Field(default="users.User")
    ROOT_URLCONF: str = Field(default="mitxpro.urls")
    WSGI_APPLICATION: str = Field(default="mitxpro.wsgi.application")
    SESSION_ENGINE: str = Field(
        default="django.contrib.sessions.backends.signed_cookies"
    )
    LOGIN_REDIRECT_URL: str = Field(default="/")
    LOGIN_URL: str = Field(default="/signin")
    LOGIN_ERROR_URL: str = Field(default="/signin")
    LANGUAGE_CODE: str = Field(default="en-us")
    TIME_ZONE: str = Field(default="UTC")
    USE_I18N: bool = Field(default=True)
    USE_TZ: bool = Field(default=True)
    ROBOTS_USE_HOST: bool = Field(default=False)
    SILKY_ANALYZE_QUERIES: bool = Field(default=True)
    STATIC_URL: str = Field(default="/static/")
    STATICFILES_FINDERS: list[str] = Field(
        default_factory=lambda: [
            "django.contrib.staticfiles.finders.FileSystemFinder",
            "django.contrib.staticfiles.finders.AppDirectoriesFinder",
        ]
    )
    STATIC_ROOT: str = Field(default="staticfiles")
    STATICFILES_DIRS: tuple[str, ...] = Field(
        default_factory=lambda: (f"{BASE_DIR}/static",)
    )
    MEDIA_URL: str = Field(default="/media/")
    HIJACK_INSERT_BEFORE: str = Field(default="</body>")
    WAGTAILEMBEDS_FINDERS: list[dict[str, str]] = Field(
        default_factory=lambda: [
            {"class": "cms.embeds.YouTubeEmbedFinder"},
            {"class": "wagtail.embeds.finders.oembed"},
        ]
    )
    OAUTH2_PROVIDER_ACCESS_TOKEN_MODEL: str = Field(
        default="oauth2_provider.AccessToken"
    )
    OAUTH2_PROVIDER_APPLICATION_MODEL: str = Field(
        default="oauth2_provider.Application"
    )
    OAUTH2_PROVIDER_REFRESH_TOKEN_MODEL: str = Field(
        default="oauth2_provider.RefreshToken"
    )
    REST_FRAMEWORK: dict[str, Any] = Field(
        default_factory=lambda: {
            "DEFAULT_AUTHENTICATION_CLASSES": (
                "rest_framework.authentication.SessionAuthentication",
                "oauth2_provider.contrib.rest_framework.OAuth2Authentication",
            ),
            "DEFAULT_PERMISSION_CLASSES": (
                "rest_framework.permissions.IsAuthenticated",
            ),
            "EXCEPTION_HANDLER": "mitxpro.exceptions.exception_handler",
            "TEST_REQUEST_DEFAULT_FORMAT": "json",
        }
    )
    PASSWORD_RESET_CONFIRM_URL: str = Field(
        default="password_reset/confirm/{uid}/{token}/"  # pragma: allowlist secret
    )
    DJOSER: dict[str, Any] = Field(
        default_factory=lambda: {
            "PASSWORD_RESET_CONFIRM_URL": "password_reset/confirm/{uid}/{token}/",  # pragma: allowlist secret
            "SET_PASSWORD_RETYPE": False,
            "LOGOUT_ON_PASSWORD_CHANGE": False,
            "PASSWORD_RESET_CONFIRM_RETYPE": True,
            "PASSWORD_RESET_SHOW_EMAIL_NOT_FOUND": False,
            "EMAIL": {
                "password_reset": "mitol.authentication.views.djoser_views.CustomPasswordResetEmail"  # pragma: allowlist secret
            },
            "SERIALIZERS": {
                "password_reset": "mitol.authentication.serializers.djoser_serializers.CustomSendEmailResetSerializer"  # pragma: allowlist secret
            },
        }
    )
    MITOL_COMMON_USER_FACTORY: str = Field(default="users.factories.UserFactory")
    MITOL_MAIL_MESSAGE_CLASSES: list[str] = Field(
        default_factory=lambda: ["courses.messages.DigitalCredentialAvailableMessage"]
    )
    MITOL_MAIL_FORMAT_RECIPIENT_FUNC: str = Field(
        default="users.utils.format_recipient"
    )
    MITOL_DIGITAL_CREDENTIALS_BUILD_CREDENTIAL_FUNC: str = Field(
        default="courses.credentials.build_digital_credential"
    )
    DEFAULT_AUTO_FIELD: str = Field(default="django.db.models.AutoField")
    AUTHENTICATION_BACKENDS: tuple[str, ...] = Field(
        default_factory=lambda: (
            "social_core.backends.email.EmailAuth",
            "oauth2_provider.backends.OAuth2Backend",
            "django.contrib.auth.backends.ModelBackend",
        )
    )
    SOCIAL_AUTH_LOGIN_ERROR_URL: str = Field(default="login")
    SOCIAL_AUTH_EMAIL_FORM_URL: str = Field(default="login")
    SOCIAL_AUTH_EMAIL_FORM_HTML: str = Field(default="login.html")
    SOCIAL_AUTH_EMAIL_USER_FIELDS: list[str] = Field(
        default_factory=lambda: ["username", "email", "name", "password"]
    )
    SOCIAL_AUTH_EMAIL_FORCE_EMAIL_VALIDATION: bool = Field(default=True)
    SOCIAL_AUTH_EMAIL_VALIDATION_FUNCTION: str = Field(
        default="mail.verification_api.send_verification_email"
    )
    SOCIAL_AUTH_EMAIL_VALIDATION_URL: str = Field(default="/")
    SOCIAL_AUTH_PIPELINE: tuple[str, ...] = Field(
        default_factory=lambda: (
            "authentication.pipeline.user.forbid_hijack",
            "social_core.pipeline.social_auth.social_details",
            "social_core.pipeline.social_auth.social_uid",
            "social_core.pipeline.social_auth.auth_allowed",
            "social_core.pipeline.social_auth.social_user",
            "social_core.pipeline.social_auth.associate_by_email",
            "authentication.pipeline.user.validate_email_auth_request",
            "authentication.pipeline.user.validate_email",
            "authentication.pipeline.user.validate_password",
            "social_core.pipeline.mail.mail_validation",
            "authentication.pipeline.user.send_user_to_hubspot",
            "authentication.pipeline.user.get_username",
            "authentication.pipeline.user.create_user_via_email",
            "authentication.pipeline.compliance.verify_exports_compliance",
            "social_core.pipeline.social_auth.associate_user",
            "authentication.pipeline.user.activate_user",
            "authentication.pipeline.user.create_courseware_user",
            "authentication.pipeline.user.create_profile",
            "social_core.pipeline.social_auth.load_extra_data",
            "social_core.pipeline.user.user_details",
            "authentication.pipeline.user.sync_user_to_hubspot",
        )
    )
    SHEETS_REQ_EMAIL_COL: int = Field(default=7)
    SHEETS_REQ_PROCESSED_COL: int = Field(default=8)
    SHEETS_REQ_ERROR_COL: int = Field(default=9)
    # Populated by `_build_derived_aliases` below, matching mitxpro/settings.py.
    SHEETS_REQ_CALCULATED_COLUMNS: set[int] = Field(default_factory=set)
    SHEETS_REQ_PROCESSED_COL_LETTER: str = Field(default="")
    SHEETS_REQ_ERROR_COL_LETTER: str = Field(default="")

    # =====================================================================
    # Fields fully derived from other fields. Defaults below are
    # placeholders overwritten by the validators further down; they exist
    # so the field is present/typed even before validation runs.
    # =====================================================================
    BASE_DIR: str = Field(default_factory=lambda: BASE_DIR)
    VERSION: str = Field(default_factory=lambda: VERSION)
    HOSTNAME: str = Field(default="")
    WEBPACK_LOADER: dict[str, Any] = Field(default_factory=dict)
    INSTALLED_APPS: tuple[str, ...] = Field(default_factory=tuple)
    MIDDLEWARE: tuple[str, ...] = Field(default_factory=tuple)
    DEFAULT_DATABASE_CONFIG: dict[str, Any] = Field(default_factory=dict)
    DATABASES: dict[str, Any] = Field(default_factory=dict)
    STORAGES: dict[str, Any] = Field(default_factory=dict)
    AWS_S3_CUSTOM_DOMAIN: str | None = Field(default=None)
    CACHES: dict[str, Any] = Field(default_factory=dict)
    ANYMAIL: dict[str, Any] = Field(default_factory=dict)
    ADMINS: tuple[tuple[str, str], ...] = Field(default_factory=tuple)
    OAUTH2_PROVIDER: dict[str, Any] = Field(default_factory=dict)
    HUBSPOT_CONFIG: dict[str, Any] = Field(default_factory=dict)
    LOGGING: dict[str, Any] = Field(default_factory=dict)
    SOCIAL_AUTH_ALLOWED_REDIRECT_HOSTS: list[str] = Field(default_factory=list)
    WAGTAILADMIN_BASE_URL: str = Field(default="")
    WAGTAIL_SITE_NAME: str = Field(default="")
    MITOL_AUTHENTICATION_FROM_EMAIL: str = Field(default="")
    MITOL_AUTHENTICATION_REPLY_TO_EMAIL: str = Field(default="")
    MITOL_MAIL_FROM_EMAIL: str = Field(default="")
    MITOL_MAIL_REPLY_TO_ADDRESS: str = Field(default="")
    MITOL_MAIL_RECIPIENT_OVERRIDE: str | None = Field(default=None)
    NPLUSONE_LOGGER: Any = Field(default=None)
    NPLUSONE_LOG_LEVEL: int = Field(default=40)  # logging.ERROR
    TEMPLATES: list[dict[str, Any]] = Field(
        default_factory=lambda: [
            {
                "BACKEND": "django.template.backends.django.DjangoTemplates",
                "DIRS": [f"{BASE_DIR}/templates"],
                "APP_DIRS": True,
                "OPTIONS": {
                    "context_processors": [
                        "django.template.context_processors.debug",
                        "django.template.context_processors.request",
                        "django.contrib.auth.context_processors.auth",
                        "django.contrib.messages.context_processors.messages",
                        "social_django.context_processors.backends",
                        "social_django.context_processors.login_redirect",
                        "mitxpro.context_processors.api_keys",
                        "mitxpro.context_processors.configuration_context",
                    ]
                },
            }
        ]
    )
    USE_CELERY: bool = Field(default=True)
    INTERNAL_IPS: tuple[str, ...] = Field(default_factory=tuple)

    # mitxpro/settings.py stores these under a Django-facing attribute name
    # that differs from the environment variable that configures it (e.g.
    # ``SITE_BASE_URL`` is read from ``MITXPRO_BASE_URL``). The raw,
    # env-sourced fields above hold the actual configured value; these are
    # populated from them by `_build_derived_aliases`.
    SITE_BASE_URL: str = Field(default="")
    SITE_ID: int = Field(default=1)
    ADMIN_EMAIL: str = Field(default="")
    SECURE_SSL_REDIRECT: bool = Field(default=True)
    SECURE_SSL_HOST: str | None = Field(default=None)
    EMAIL_BACKEND: str = Field(default="django.core.mail.backends.smtp.EmailBackend")
    EMAIL_HOST: str = Field(default="localhost")
    EMAIL_PORT: int = Field(default=25)
    EMAIL_HOST_USER: str = Field(default="")
    EMAIL_HOST_PASSWORD: str = Field(default="")
    EMAIL_USE_TLS: bool = Field(default=False)
    DEFAULT_FROM_EMAIL: str = Field(default="webmaster@localhost")
    EMAIL_SUPPORT: str = Field(default="support@localhost")
    NOTIFICATION_EMAIL_BACKEND: str = Field(
        default="anymail.backends.mailgun.EmailBackend"
    )
    LOG_LEVEL: str = Field(default="INFO")
    # `settings.ENVIRONMENT` (used pervasively by application code) sourced
    # from the `MITXPRO_ENVIRONMENT` env var.
    ENVIRONMENT: str = Field(default="dev")

    # =====================================================================
    # Validators
    # =====================================================================

    @model_validator(mode="after")
    def _apply_env_name_aliases(self) -> AqueductSettings:
        """Copy raw, env-named fields onto the Django-facing attribute name.

        mitxpro/settings.py declares several settings with
        ``X = get_string(name="ENV_VAR_NAME", ...)`` where ``X`` (the actual
        Django setting / attribute other code reads) differs from
        ``ENV_VAR_NAME`` (the environment variable that configures it). Must
        run before every other validator, since several of them reference
        these Django-facing names (e.g. ``SITE_BASE_URL``, ``ADMIN_EMAIL``).
        """
        self.SITE_BASE_URL = self.MITXPRO_BASE_URL
        self.SITE_ID = self.MITXPRO_SITE_ID
        self.ADMIN_EMAIL = self.MITXPRO_ADMIN_EMAIL
        self.SECURE_SSL_REDIRECT = self.MITXPRO_SECURE_SSL_REDIRECT
        self.SECURE_SSL_HOST = self.MITXPRO_SECURE_SSL_HOST
        self.EMAIL_BACKEND = self.MITXPRO_EMAIL_BACKEND
        self.EMAIL_HOST = self.MITXPRO_EMAIL_HOST
        self.EMAIL_PORT = self.MITXPRO_EMAIL_PORT
        self.EMAIL_HOST_USER = self.MITXPRO_EMAIL_USER
        self.EMAIL_HOST_PASSWORD = self.MITXPRO_EMAIL_PASSWORD
        self.EMAIL_USE_TLS = self.MITXPRO_EMAIL_TLS
        self.NOTIFICATION_EMAIL_BACKEND = self.MITXPRO_NOTIFICATION_EMAIL_BACKEND
        self.LOG_LEVEL = self.MITXPRO_LOG_LEVEL
        self.INTERNAL_IPS = (self.HOST_IP,)
        self.ENVIRONMENT = self.MITXPRO_ENVIRONMENT
        self.DEFAULT_FROM_EMAIL = self.MITXPRO_FROM_EMAIL
        self.EMAIL_SUPPORT = (
            self.MITXPRO_SUPPORT_EMAIL
            if self.MITXPRO_SUPPORT_EMAIL is not None
            else (self.MAILGUN_RECIPIENT_OVERRIDE or "support@localhost")
        )
        return self

    @model_validator(mode="after")
    def _resolve_redis_urls(self) -> AqueductSettings:
        """Mirror the `_redis_url` fallback chain in mitxpro/settings.py.

        ``REDISCLOUD_URL`` wins when set; otherwise fall back to
        ``REDIS_URL``. Any of ``CELERY_BROKER_URL``, ``CELERY_RESULT_BACKEND``,
        ``CELERY_REDBEAT_REDIS_URL``, or ``WAGTAIL_CACHE_URL`` that were not
        explicitly set default to this resolved Redis URL.
        """
        redis_url = (
            self.REDISCLOUD_URL if self.REDISCLOUD_URL is not None else self.REDIS_URL
        )
        if self.CELERY_BROKER_URL is None:
            self.CELERY_BROKER_URL = redis_url
        if self.CELERY_RESULT_BACKEND is None:
            self.CELERY_RESULT_BACKEND = redis_url
        if self.CELERY_REDBEAT_REDIS_URL is None:
            self.CELERY_REDBEAT_REDIS_URL = redis_url
        if self.WAGTAIL_CACHE_URL is None:
            self.WAGTAIL_CACHE_URL = redis_url
        return self

    @model_validator(mode="after")
    def _scan_features(self) -> AqueductSettings:
        """Reproduce `mitol.common.envs.get_features()`: scan `FEATURE_*` env vars.

        Values must be exactly ``"true"`` or ``"false"`` (case-insensitive),
        matching `mitol.common.envs.parse_bool`; anything else is dropped
        rather than raising, since this runs post-hoc over `os.environ`
        instead of at declaration time.
        """
        prefix = "FEATURE_"
        features: dict[str, bool] = {}
        for key, value in os.environ.items():
            if not key.startswith(prefix):
                continue
            lowered = value.strip().lower()
            if lowered in ("true", "false"):
                features[key[len(prefix) :]] = lowered == "true"
        self.FEATURES = features
        return self

    @model_validator(mode="after")
    def _validate_s3_config(self) -> AqueductSettings:
        """Mirror the S3 cross-field validation in mitxpro/settings.py."""
        if self.MITXPRO_USE_S3 and (
            not self.AWS_ACCESS_KEY_ID
            or not self.AWS_SECRET_ACCESS_KEY
            or not self.AWS_STORAGE_BUCKET_NAME
        ):
            raise ImproperlyConfigured(
                "You have enabled S3 support, but are missing one of "
                "AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, or "
                "AWS_STORAGE_BUCKET_NAME"
            )
        return self

    @model_validator(mode="after")
    def _build_installed_apps_and_middleware(self) -> AqueductSettings:
        """Reconstruct the ENVIRONMENT/DEBUG-conditional app & middleware lists."""
        installed_apps = (
            "django.contrib.admin",
            "django.contrib.auth",
            "django.contrib.contenttypes",
            "django.contrib.sessions",
            "django.contrib.messages",
            "django.contrib.staticfiles",
            "django.contrib.humanize",
            "django.contrib.sites",
            "django.contrib.sitemaps",
            "django_user_agents",
            "social_django",
            "oauth2_provider",
            "rest_framework",
            "anymail",
            "django_filters",
            # WAGTAIL
            "wagtail.contrib.forms",
            "wagtail.contrib.redirects",
            "wagtail.contrib.table_block",
            "wagtail.contrib.routable_page",
            "wagtail.embeds",
            "wagtail.sites",
            "users.apps.MitxproWagtailUsersAppConfig",
            "wagtail.snippets",
            "wagtail.documents",
            "wagtail.images",
            "wagtail.search",
            "wagtail.admin",
            "wagtail",
            "wagtailmetadata",
            "modelcluster",
            "taggit",
            "wagtail.api.v2",
            # django-robots
            "robots",
            # project apps
            "mitxpro",
            "authentication",
            "courses",
            "mail.apps.MailApp",
            "users",
            "cms",
            "compliance",
            "courseware",
            "sheets",
            "affiliate",
            # must be after "users" to pick up custom user model
            "b2b_ecommerce",
            "ecommerce",
            "hijack",
            "hijack.contrib.admin",
            "hubspot_xpro",
            "voucher",
            "maxmind",
            # ol-django apps, must be after this project's apps for template precedence
            "mitol.hubspot_api.apps.HubspotApiApp",
            "mitol.common.apps.CommonApp",
            "mitol.observability.apps.ObservabilityConfig",
            "mitol.digitalcredentials.apps.DigitalCredentialsApp",
            "mitol.mail.apps.MailApp",
            "mitol.oauth_toolkit_extensions.apps.OAuthToolkitExtensionsApp",
            "mitol.authentication.apps.TransitionalAuthenticationApp",
            "mitol.olposthog.apps.OlPosthog",
        )
        if self.ENVIRONMENT not in ("production", "prod"):
            installed_apps += ("localdev.seed",)
        if not self.WEBPACK_DISABLE_LOADER_STATS:
            installed_apps += ("webpack_loader",)

        middleware = (
            "django.middleware.security.SecurityMiddleware",
            "mitxpro.middleware.HostnameRedirectMiddleware",
            "django.contrib.sessions.middleware.SessionMiddleware",
            "affiliate.middleware.AffiliateMiddleware",
            "oauth2_provider.middleware.OAuth2TokenMiddleware",
            "django.middleware.common.CommonMiddleware",
            "django.middleware.csrf.CsrfViewMiddleware",
            "django.contrib.auth.middleware.AuthenticationMiddleware",
            "hijack.middleware.HijackUserMiddleware",
            "django.contrib.messages.middleware.MessageMiddleware",
            "django.middleware.clickjacking.XFrameOptionsMiddleware",
            "django.contrib.sites.middleware.CurrentSiteMiddleware",
            "django_user_agents.middleware.UserAgentMiddleware",
            "wagtail.contrib.redirects.middleware.RedirectMiddleware",
        )
        if self.DEBUG:
            installed_apps += ("nplusone.ext.django", "silk")
            middleware += (
                "nplusone.ext.django.NPlusOneMiddleware",
                "silk.middleware.SilkyMiddleware",
            )
            installed_apps += ("debug_toolbar",)
            middleware = (
                "debug_toolbar.middleware.DebugToolbarMiddleware",
                *middleware,
            )

        self.INSTALLED_APPS = installed_apps
        self.MIDDLEWARE = middleware
        return self

    @model_validator(mode="after")
    def _build_static_and_storage(self) -> AqueductSettings:
        """Mirror the CLOUDFRONT_DIST-conditional STATIC_URL/STORAGES logic."""
        static_url = "/static/"
        if self.CLOUDFRONT_DIST:
            static_url = urljoin(
                f"https://{self.CLOUDFRONT_DIST}.cloudfront.net", static_url
            )
        self.STATIC_URL = static_url

        storages: dict[str, Any] = {
            "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
            "staticfiles": {
                "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
            },
        }
        if self.MITXPRO_USE_S3:
            if self.CLOUDFRONT_DIST:
                self.AWS_S3_CUSTOM_DOMAIN = f"{self.CLOUDFRONT_DIST}.cloudfront.net"
            storages["default"] = {
                "BACKEND": "storages.backends.s3boto3.S3Boto3Storage"
            }
        self.STORAGES = storages
        return self

    @model_validator(mode="after")
    def _build_webpack_loader(self) -> AqueductSettings:
        self.WEBPACK_LOADER = {
            "DEFAULT": {
                "CACHE": not self.DEBUG,
                "BUNDLE_DIR_NAME": "bundles/",
                "STATS_FILE": f"{self.BASE_DIR}/webpack-stats.json",
                "POLL_INTERVAL": 0.1,
                "TIMEOUT": None,
                "IGNORE": [r".+\.hot-update\.+", r".+\.js\.map"],
            }
        }
        return self

    @model_validator(mode="after")
    def _build_databases(self) -> AqueductSettings:
        default_database_config = dj_database_url.parse(self.DATABASE_URL)
        default_database_config["CONN_MAX_AGE"] = self.MITXPRO_DB_CONN_MAX_AGE
        default_database_config["DISABLE_SERVER_SIDE_CURSORS"] = (
            self.MITXPRO_DB_DISABLE_SS_CURSORS
        )
        if self.MITXPRO_DB_DISABLE_SSL:
            default_database_config["OPTIONS"] = {}
        else:
            default_database_config["OPTIONS"] = {"sslmode": "require"}
        self.DEFAULT_DATABASE_CONFIG = default_database_config
        self.DATABASES = {"default": default_database_config}
        return self

    @model_validator(mode="after")
    def _build_caches(self) -> AqueductSettings:
        self.CACHES = {
            "default": {
                "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
                "LOCATION": "local-in-memory-cache",
            },
            "redis": {
                "BACKEND": "django_redis.cache.RedisCache",
                "LOCATION": self.CELERY_BROKER_URL,
                "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
            },
            "renditions": {
                "BACKEND": self.WAGTAIL_CACHE_BACKEND,
                "LOCATION": self.WAGTAIL_CACHE_URL,
                "TIMEOUT": 31_536_000,  # 1 year
                "KEY_PREFIX": "wag",
                "OPTIONS": {
                    "MAX_ENTRIES": self.WAGTAIL_CACHE_MAX_ENTRIES,
                    "CLIENT_CLASS": "django_redis.client.DefaultClient",
                },
            },
            "durable": {
                "BACKEND": "django.core.cache.backends.db.DatabaseCache",
                "LOCATION": "durable_cache",
            },
        }
        return self

    @model_validator(mode="after")
    def _build_social_auth_redirect_hosts(self) -> AqueductSettings:
        self.SOCIAL_AUTH_ALLOWED_REDIRECT_HOSTS = [urlparse(self.SITE_BASE_URL).netloc]
        return self

    @model_validator(mode="after")
    def _build_anymail_and_admins(self) -> AqueductSettings:
        self.ANYMAIL = {
            "MAILGUN_API_KEY": self.MAILGUN_KEY,
            "MAILGUN_SENDER_DOMAIN": self.MAILGUN_SENDER_DOMAIN,
        }
        self.ADMINS = (("Admins", self.ADMIN_EMAIL),) if self.ADMIN_EMAIL != "" else ()
        return self

    @model_validator(mode="after")
    def _build_hubspot_config(self) -> AqueductSettings:
        self.HUBSPOT_CONFIG = {
            "HUBSPOT_NEW_COURSES_FORM_GUID": self.HUBSPOT_NEW_COURSES_FORM_GUID,
            "HUBSPOT_FOOTER_FORM_GUID": self.HUBSPOT_FOOTER_FORM_GUID,
            "HUBSPOT_PORTAL_ID": self.HUBSPOT_PORTAL_ID,
            "HUBSPOT_CREATE_USER_FORM_ID": self.HUBSPOT_CREATE_USER_FORM_ID,
            "HUBSPOT_ENTERPRISE_PAGE_FORM_ID": self.HUBSPOT_ENTERPRISE_PAGE_FORM_ID,
        }
        return self

    @model_validator(mode="after")
    def _build_oauth2_provider(self) -> AqueductSettings:
        self.OAUTH2_PROVIDER = {
            # Disable PKCE requirement to maintain backward compatibility with
            # existing OAuth clients (PKCE_REQUIRED changed default to True in
            # django-oauth-toolkit 2.0.0)
            "PKCE_REQUIRED": False,
            "SCOPES": {
                "read": "Read scope",
                "write": "Write scope",
                "user:read": "Can read user and profile data",
                "digitalcredentials": "Can read and write Digital Credentials data",
            },
            "DEFAULT_SCOPES": ["user:read"],
            "SCOPES_BACKEND_CLASS": "mitol.oauth_toolkit_extensions.backends.ApplicationAccessOrSettingsScopes",
            "ERROR_RESPONSE_WITH_SCOPES": self.DEBUG,
            "ALLOWED_REDIRECT_URI_SCHEMES": self.OAUTH2_PROVIDER_ALLOWED_REDIRECT_URI_SCHEMES,
            "REFRESH_TOKEN_EXPIRE_SECONDS": self.REFRESH_TOKEN_EXPIRE_SECONDS,
        }
        return self

    @model_validator(mode="after")
    def _build_logging(self) -> AqueductSettings:
        from mitol.observability.settings.logging import LOGGING  # noqa: PLC0415

        self.LOGGING = LOGGING
        return self

    @model_validator(mode="after")
    def _build_celery_beat_schedule(self) -> AqueductSettings:
        """Rebuild CELERY_BEAT_SCHEDULE, including its crontab/OffsettingSchedule values.

        Must run after `_scan_features` so `FEATURES` is populated.
        """
        # Computed here (rather than in `_build_derived_aliases`, which runs
        # later) because it's needed immediately below.
        self.REPAIR_COURSEWARE_USERS_OFFSET = int(
            self.REPAIR_COURSEWARE_USERS_FREQUENCY / 2
        )

        schedule: dict[str, Any] = {
            "retry-failed-edx-enrollments": {
                "task": "courseware.tasks.retry_failed_edx_enrollments",
                "schedule": self.RETRY_FAILED_EDX_ENROLLMENT_FREQUENCY,
            },
            "repair-faulty-edx-users": {
                "task": "courseware.tasks.repair_faulty_courseware_users",
                "schedule": OffsettingSchedule(
                    run_every=timedelta(seconds=self.REPAIR_COURSEWARE_USERS_FREQUENCY),
                    offset=timedelta(seconds=self.REPAIR_COURSEWARE_USERS_OFFSET),
                ),
            },
            "generate-course-certificate": {
                "task": "courses.tasks.generate_course_certificates",
                "schedule": crontab(
                    minute=0,
                    hour=self.CRON_COURSE_CERTIFICATES_HOURS,
                    day_of_week=self.CRON_COURSE_CERTIFICATES_DAYS or "*",
                    day_of_month="*",
                    month_of_year="*",
                ),
            },
            "sync-courseruns-data": {
                "task": "courses.tasks.sync_courseruns_data",
                "schedule": crontab(
                    minute=0,
                    hour=self.CRON_COURSERUN_SYNC_HOURS,
                    day_of_week=self.CRON_COURSERUN_SYNC_DAYS or "*",
                    day_of_month="*",
                    month_of_year="*",
                ),
            },
            "sync-external-course-runs": {
                "task": "courses.tasks.task_sync_external_course_runs",
                "schedule": crontab(
                    minute="0",
                    hour=self.CRON_EXTERNAL_COURSERUN_SYNC_HOURS,
                    day_of_week=self.CRON_EXTERNAL_COURSERUN_SYNC_DAYS or "*",
                    day_of_month="*",
                    month_of_year="*",
                ),
            },
            "delete-expired-baskets": {
                "task": "ecommerce.tasks.delete_expired_baskets",
                "schedule": crontab(
                    minute=0,
                    hour=self.CRON_BASKET_DELETE_HOURS,
                    day_of_week=self.CRON_BASKET_DELETE_DAYS,
                    day_of_month="*",
                    month_of_year="*",
                ),
            },
            "renew_all_file_watches": {
                "task": "sheets.tasks.renew_all_file_watches",
                "schedule": (
                    self.DRIVE_WEBHOOK_EXPIRATION_MINUTES
                    - self.DRIVE_WEBHOOK_RENEWAL_PERIOD_MINUTES
                )
                * 60,
            },
            "clear-expired-tokens": {
                "task": "mitxpro.tasks.clear_expired_tokens",
                "schedule": crontab(minute=0, hour=9, day_of_week=1),
            },
        }

        alt_sheets_processing = self.FEATURES.get("COUPON_SHEETS_ALT_PROCESSING")
        if alt_sheets_processing:
            schedule["handle-coupon-request-sheet"] = {
                "task": "sheets.tasks.handle_unprocessed_coupon_requests",
                "schedule": self.SHEETS_MONITORING_FREQUENCY,
            }

        schedule["update-assignment-delivery-dates"] = {
            "task": "sheets.tasks.update_incomplete_assignment_delivery_statuses",
            "schedule": OffsettingSchedule(
                run_every=timedelta(seconds=self.SHEETS_MONITORING_FREQUENCY),
                offset=timedelta(
                    seconds=0 if not alt_sheets_processing else self.SHEETS_TASK_OFFSET
                ),
            ),
        }

        self.CELERY_BEAT_SCHEDULE = schedule
        return self

    @model_validator(mode="after")
    def _build_derived_aliases(self) -> AqueductSettings:
        """Copy resolved primitives onto the Django-facing setting names.

        mitxpro/settings.py stores several settings under a different
        attribute name than the environment variable that configures them
        (or derives one setting entirely from another). This validator
        reproduces those relationships.
        """
        self.HOSTNAME = platform.node().split(".")[0]

        self.WAGTAILADMIN_BASE_URL = self.SITE_BASE_URL
        self.WAGTAIL_SITE_NAME = self.SITE_NAME

        # mitxpro/settings.py fully overrides the djoser-sourced
        # MITOL_AUTHENTICATION_FROM_EMAIL with MAILGUN_FROM_EMAIL, and
        # introduces a new MITOL_AUTHENTICATION_REPLY_TO_EMAIL alongside the
        # pre-existing MITOL_AUTHENTICATION_REPLY_TO_ADDRESS.
        self.MITOL_AUTHENTICATION_FROM_EMAIL = self.MAILGUN_FROM_EMAIL
        self.MITOL_AUTHENTICATION_REPLY_TO_EMAIL = self.MITXPRO_REPLY_TO_ADDRESS

        self.MITOL_MAIL_FROM_EMAIL = self.MAILGUN_FROM_EMAIL
        self.MITOL_MAIL_REPLY_TO_ADDRESS = self.MITXPRO_REPLY_TO_ADDRESS
        self.MITOL_MAIL_RECIPIENT_OVERRIDE = self.MAILGUN_RECIPIENT_OVERRIDE

        self.OPENEDX_BASE_REDIRECT_URL = (
            self.OPENEDX_BASE_REDIRECT_URL or self.OPENEDX_API_BASE_URL
        )

        self.SHEETS_DATE_TIMEZONE = ZoneInfo(self.SHEETS_DATE_TIMEZONE_NAME)

        uppercase_a_ord = ord("A")
        self.SHEETS_REQ_CALCULATED_COLUMNS = {
            self.SHEETS_REQ_EMAIL_COL,
            self.SHEETS_REQ_PROCESSED_COL,
            self.SHEETS_REQ_ERROR_COL,
        }
        self.SHEETS_REQ_PROCESSED_COL_LETTER = chr(
            self.SHEETS_REQ_PROCESSED_COL + uppercase_a_ord
        )
        self.SHEETS_REQ_ERROR_COL_LETTER = chr(
            self.SHEETS_REQ_ERROR_COL + uppercase_a_ord
        )

        self.NPLUSONE_LOGGER = logging.getLogger("nplusone")

        return self
