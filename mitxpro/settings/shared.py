"""
Django shared settings for mitxpro.
"""
import logging
import os
import platform
from datetime import timedelta
from urllib.parse import urljoin, urlparse

import dj_database_url
import pytz
from celery.schedules import crontab
from django.core.exceptions import ImproperlyConfigured
from mitol.common.envs import (
    get_bool,
    get_delimited_list,
    get_features,
    get_int,
    get_string,
    import_settings_modules,
)
from mitol.common.settings.webpack import *  # pylint: disable=wildcard-import,unused-wildcard-import
from mitol.digitalcredentials.settings import *  # pylint: disable=wildcard-import,unused-wildcard-import
from redbeat import RedBeatScheduler

from mitxpro.celery_utils import OffsettingSchedule
from mitxpro.sentry import init_sentry
from mitxpro.settings import VERSION

ENVIRONMENT = get_string(
    name="MITXPRO_ENVIRONMENT",
    default="dev",
    description="The execution environment that the app is in (e.g. dev, staging, prod)",
    required=True,
)
# this is only available to heroku review apps
HEROKU_APP_NAME = get_string(
    name="HEROKU_APP_NAME", default=None, description="The name of the review app"
)

# initialize Sentry before doing anything else so we capture any config errors
SENTRY_DSN = get_string(
    name="SENTRY_DSN", default="", description="The connection settings for Sentry"
)
SENTRY_LOG_LEVEL = get_string(
    name="SENTRY_LOG_LEVEL", default="ERROR", description="The log level for Sentry"
)
init_sentry(
    dsn=SENTRY_DSN,
    environment=ENVIRONMENT,
    version=VERSION,
    log_level=SENTRY_LOG_LEVEL,
    heroku_app_name=HEROKU_APP_NAME,
)

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SITE_BASE_URL = get_string(
    name="MITXPRO_BASE_URL",
    default=None,
    description="Base url for the application in the format PROTOCOL://HOSTNAME[:PORT]",
    required=True,
)

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = get_string(
    name="SECRET_KEY", default=None, description="Django secret key.", required=True
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = get_bool(
    name="DEBUG",
    default=False,
    dev_only=True,
    description="Set to True to enable DEBUG mode. Don't turn on in production.",
)


ALLOWED_HOSTS = ["*"]

CSRF_TRUSTED_ORIGINS = get_delimited_list(
    name="CSRF_TRUSTED_ORIGINS",
    default=[],
    description="Comma separated string of trusted domains that should be CSRF exempt",
)

SECURE_SSL_REDIRECT = get_bool(
    name="MITXPRO_SECURE_SSL_REDIRECT",
    default=True,
    description="Application-level SSL redirect setting.",
)

SECURE_SSL_HOST = get_string(
    name="MITXPRO_SECURE_SSL_HOST",
    default=None,
    description="Hostame to redirect non-secure requests to. "
    "Overrides value from HOST header.",
)

SITE_ID = get_string(
    name="MITXPRO_SITE_ID",
    default=1,
    description="The default site id for django sites framework",
)

# configure a custom user model
AUTH_USER_MODEL = "users.User"

DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

MIDDLEWARE = (
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django.contrib.sites.middleware.CurrentSiteMiddleware",
    "django_user_agents.middleware.UserAgentMiddleware",
    "wagtail.contrib.redirects.middleware.RedirectMiddleware",
)

INSTALLED_APPS = (
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "django.contrib.sites",
    "django_user_agents",
    "social_django",
    "server_status",
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
    "wagtail.users",
    "wagtail.snippets",
    "wagtail.documents",
    "wagtail.images",
    "wagtail.search",
    "wagtail.admin",
    "wagtail.core",
    "wagtailmetadata",
    "modelcluster",
    "taggit",
)

# enable the nplusone profiler only in debug mode
if DEBUG:
    INSTALLED_APPS += ("nplusone.ext.django",)
    MIDDLEWARE += ("nplusone.ext.django.NPlusOneMiddleware",)

SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"

LOGIN_REDIRECT_URL = "/"
LOGIN_URL = "/signin"
LOGIN_ERROR_URL = "/signin"
LOGOUT_REDIRECT_URL = get_string(
    name="LOGOUT_REDIRECT_URL",
    default="/",
    description="Url to redirect to after logout, typically Open edX's own logout url",
)

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, "templates")],
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

# Database
# https://docs.djangoproject.com/en/2.0/ref/settings/#databases
DEFAULT_DATABASE_CONFIG = dj_database_url.parse(
    get_string(
        name="DATABASE_URL",
        default="sqlite:///{0}".format(os.path.join(BASE_DIR, "db.sqlite3")),
        description="The connection url to the Postgres database",
        required=True,
        write_app_json=False,
    )
)
DEFAULT_DATABASE_CONFIG["CONN_MAX_AGE"] = get_int(
    name="MITXPRO_DB_CONN_MAX_AGE",
    default=0,
    description="Maximum age of connection to Postgres in seconds",
)
# If True, disables server-side database cursors to prevent invalid cursor errors when using pgbouncer
DEFAULT_DATABASE_CONFIG["DISABLE_SERVER_SIDE_CURSORS"] = get_bool(
    name="MITXPRO_DB_DISABLE_SS_CURSORS",
    default=True,
    description="Disables Postgres server side cursors",
)


if get_bool(
    name="MITXPRO_DB_DISABLE_SSL",
    default=False,
    description="Disables SSL to postgres if set to True",
):
    DEFAULT_DATABASE_CONFIG["OPTIONS"] = {}
else:
    DEFAULT_DATABASE_CONFIG["OPTIONS"] = {"sslmode": "require"}

DATABASES = {"default": DEFAULT_DATABASE_CONFIG}

# Internationalization
# https://docs.djangoproject.com/en/2.0/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_L10N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.8/howto/static-files/

# Serve static files with dj-static
STATIC_URL = "/static/"
CLOUDFRONT_DIST = get_string(
    name="CLOUDFRONT_DIST",
    default=None,
    description="The Cloundfront distribution to use for static assets",
)
if CLOUDFRONT_DIST:
    STATIC_URL = urljoin(
        "https://{dist}.cloudfront.net".format(dist=CLOUDFRONT_DIST), STATIC_URL
    )

STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
]

STATIC_ROOT = "staticfiles"
STATICFILES_DIRS = (os.path.join(BASE_DIR, "static"),)


# Important to define this so DEBUG works properly
INTERNAL_IPS = (
    get_string(
        name="HOST_IP", default="127.0.0.1", description="This server's host IP"
    ),
)

# Configure e-mail settings
EMAIL_BACKEND = get_string(
    name="MITXPRO_EMAIL_BACKEND",
    default="django.core.mail.backends.smtp.EmailBackend",
    description="The default email backend to use for outgoing email. This is used in some places by django itself. See `NOTIFICATION_EMAIL_BACKEND` for the backend used for most application emails.",
)
EMAIL_HOST = get_string(
    name="MITXPRO_EMAIL_HOST",
    default="localhost",
    description="Outgoing e-mail hostname",
)
EMAIL_PORT = get_int(
    name="MITXPRO_EMAIL_PORT", default=25, description="Outgoing e-mail port"
)
EMAIL_HOST_USER = get_string(
    name="MITXPRO_EMAIL_USER", default="", description="Outgoing e-mail auth username"
)
EMAIL_HOST_PASSWORD = get_string(
    name="MITXPRO_EMAIL_PASSWORD",
    default="",
    description="Outgoing e-mail auth password",
)
EMAIL_USE_TLS = get_bool(
    name="MITXPRO_EMAIL_TLS", default=False, description="Outgoing e-mail TLS setting"
)

MITXPRO_REPLY_TO_ADDRESS = get_string(
    name="MITXPRO_REPLY_TO_ADDRESS",
    default="webmaster@localhost",
    description="E-mail to use for reply-to address of emails",
)


DEFAULT_FROM_EMAIL = get_string(
    name="MITXPRO_FROM_EMAIL",
    default="webmaster@localhost",
    description="E-mail to use for the from field",
)

MAILGUN_SENDER_DOMAIN = get_string(
    name="MAILGUN_SENDER_DOMAIN",
    default=None,
    description="The domain to send mailgun email through",
    required=True,
)
MAILGUN_KEY = get_string(
    name="MAILGUN_KEY",
    default=None,
    description="The token for authenticating against the Mailgun API",
    required=True,
)
MAILGUN_BATCH_CHUNK_SIZE = get_int(
    name="MAILGUN_BATCH_CHUNK_SIZE",
    default=1000,
    description="Maximum number of emails to send in a batch",
)
MAILGUN_RECIPIENT_OVERRIDE = get_string(
    name="MAILGUN_RECIPIENT_OVERRIDE",
    default=None,
    dev_only=True,
    description="Override the recipient for outgoing email, development only",
)
MAILGUN_FROM_EMAIL = get_string(
    name="MAILGUN_FROM_EMAIL",
    default="no-reply@localhost",
    description="Email which mail comes from",
)

EMAIL_SUPPORT = get_string(
    name="MITXPRO_SUPPORT_EMAIL",
    default=MAILGUN_RECIPIENT_OVERRIDE or "support@localhost",
    description="Email address listed for customer support",
)

NOTIFICATION_EMAIL_BACKEND = get_string(
    name="MITXPRO_NOTIFICATION_EMAIL_BACKEND",
    default="anymail.backends.mailgun.EmailBackend",
    description="The email backend to use for application emails",
)

ANYMAIL = {
    "MAILGUN_API_KEY": MAILGUN_KEY,
    "MAILGUN_SENDER_DOMAIN": MAILGUN_SENDER_DOMAIN,
}

# e-mail configurable admins
ADMIN_EMAIL = get_string(
    name="MITXPRO_ADMIN_EMAIL",
    default="",
    description="E-mail to send 500 reports to.",
    required=True,
)
if ADMIN_EMAIL != "":
    ADMINS = (("Admins", ADMIN_EMAIL),)
else:
    ADMINS = ()

# Logging configuration
LOG_LEVEL = get_string(
    name="MITXPRO_LOG_LEVEL", default="INFO", description="The log level default"
)
DJANGO_LOG_LEVEL = get_string(
    name="DJANGO_LOG_LEVEL", default="INFO", description="The log level for django"
)

# For logging to a remote syslog host
LOG_HOST = get_string(
    name="MITXPRO_LOG_HOST",
    default="localhost",
    description="Remote syslog server hostname",
)
LOG_HOST_PORT = get_int(
    name="MITXPRO_LOG_HOST_PORT", default=514, description="Remote syslog server port"
)

HOSTNAME = platform.node().split(".")[0]

# nplusone profiler logger configuration
NPLUSONE_LOGGER = logging.getLogger("nplusone")
NPLUSONE_LOG_LEVEL = logging.ERROR

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {"require_debug_false": {"()": "django.utils.log.RequireDebugFalse"}},
    "formatters": {
        "verbose": {
            "format": (
                "[%(asctime)s] %(levelname)s %(process)d [%(name)s] "
                "%(filename)s:%(lineno)d - "
                "[{hostname}] - %(message)s"
            ).format(hostname=HOSTNAME),
            "datefmt": "%Y-%m-%d %H:%M:%S",
        }
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "syslog": {
            "level": LOG_LEVEL,
            "class": "logging.handlers.SysLogHandler",
            "facility": "local7",
            "formatter": "verbose",
            "address": (LOG_HOST, LOG_HOST_PORT),
        },
        "mail_admins": {
            "level": "ERROR",
            "filters": ["require_debug_false"],
            "class": "django.utils.log.AdminEmailHandler",
        },
    },
    "loggers": {
        "django": {
            "propagate": True,
            "level": DJANGO_LOG_LEVEL,
            "handlers": ["console", "syslog"],
        },
        "django.request": {
            "handlers": ["mail_admins"],
            "level": DJANGO_LOG_LEVEL,
            "propagate": True,
        },
        "nplusone": {"handlers": ["console"], "level": "ERROR"},
    },
    "root": {"handlers": ["console", "syslog"], "level": LOG_LEVEL},
}

USE_X_FORWARDED_HOST = get_bool(
    name="USE_X_FORWARDED_HOST",
    default=False,
    description="Set HOST header to original domain accessed by user",
)
SITE_NAME = get_string(
    name="SITE_NAME", default="MIT xPRO", description="Name of the site. e.g MIT xPRO"
)
WAGTAIL_SITE_NAME = SITE_NAME

MEDIA_ROOT = get_string(
    name="MEDIA_ROOT",
    default="/var/media/",
    description="The root directory for locally stored media. Typically not used.",
)
MEDIA_URL = "/media/"
MITXPRO_USE_S3 = get_bool(
    name="MITXPRO_USE_S3",
    default=False,
    description="Use S3 for storage backend (required on Heroku)",
)

AWS_ACCESS_KEY_ID = get_string(
    name="AWS_ACCESS_KEY_ID", default=None, description="AWS Access Key for S3 storage."
)
AWS_SECRET_ACCESS_KEY = get_string(
    name="AWS_SECRET_ACCESS_KEY",
    default=None,
    description="AWS Secret Key for S3 storage.",
)
AWS_STORAGE_BUCKET_NAME = get_string(
    name="AWS_STORAGE_BUCKET_NAME", default=None, description="S3 Bucket name."
)
AWS_QUERYSTRING_AUTH = get_bool(
    name="AWS_QUERYSTRING_AUTH",
    default=False,
    description="Enables querystring auth for S3 urls",
)

# Provide nice validation of the configuration
if MITXPRO_USE_S3 and (
    not AWS_ACCESS_KEY_ID or not AWS_SECRET_ACCESS_KEY or not AWS_STORAGE_BUCKET_NAME
):
    raise ImproperlyConfigured(
        "You have enabled S3 support, but are missing one of "
        "AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, or "
        "AWS_STORAGE_BUCKET_NAME"
    )

if MITXPRO_USE_S3:
    if CLOUDFRONT_DIST:
        AWS_S3_CUSTOM_DOMAIN = "{dist}.cloudfront.net".format(dist=CLOUDFRONT_DIST)
    DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"

# Redis
REDISCLOUD_URL = get_string(
    name="REDISCLOUD_URL", default=None, description="RedisCloud connection url"
)
if REDISCLOUD_URL is not None:
    REDIS_URL = REDISCLOUD_URL
else:
    REDIS_URL = get_string(
        name="REDIS_URL", default=None, description="Redis URL for non-production use"
    )

# Wagtail
WAGTAIL_CACHE_BACKEND = get_string(
    name="WAGTAIL_CACHE_BACKEND",
    default="django_redis.cache.RedisCache",
    description="The caching backend to be used for Wagtail image renditions",
)
WAGTAIL_CACHE_URL = get_string(
    name="WAGTAIL_CACHE_URL",
    default=REDIS_URL,
    description="URL for Wagtail image renditions cache",
)
WAGTAIL_CACHE_MAX_ENTRIES = get_int(
    name="WAGTAIL_CACHE_MAX_ENTRIES",
    default=200,
    description="The maximum number of cache entries for Wagtail images",
)
WAGTAILEMBEDS_FINDERS = [
    {"class": "cms.embeds.YouTubeEmbedFinder"},
    {"class": "wagtail.embeds.finders.oembed"},
]

# django cache back-ends
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "local-in-memory-cache",
    },
    "renditions": {
        "BACKEND": WAGTAIL_CACHE_BACKEND,
        "LOCATION": WAGTAIL_CACHE_URL,
        "TIMEOUT": 31_536_000,  # 1 year
        "KEY_PREFIX": "wag",
        "OPTIONS": {
            "MAX_ENTRIES": WAGTAIL_CACHE_MAX_ENTRIES,
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    },
}


# Hijack
HIJACK_ALLOW_GET_REQUESTS = True
HIJACK_LOGOUT_REDIRECT_URL = "/admin/users/user"
HIJACK_REGISTER_ADMIN = False
