"""
Django settings for mitxpro.
"""
import logging
import os
import platform
from urllib.parse import urljoin, urlparse

import dj_database_url
from django.core.exceptions import ImproperlyConfigured

from mitxpro.envs import get_any, get_bool, get_int, get_string

VERSION = "0.4.0"

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SITE_BASE_URL = get_string("MITXPRO_BASE_URL", None)
if not SITE_BASE_URL:
    raise ImproperlyConfigured("MITXPRO_BASE_URL is not set")

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = get_string("SECRET_KEY", None)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = get_bool("DEBUG", False)

ENVIRONMENT = get_string("MITXPRO_ENVIRONMENT", "dev")

ALLOWED_HOSTS = ["*"]

SECURE_SSL_REDIRECT = get_bool("MITXPRO_SECURE_SSL_REDIRECT", True)

WEBPACK_LOADER = {
    "DEFAULT": {
        "CACHE": not DEBUG,
        "BUNDLE_DIR_NAME": "bundles/",
        "STATS_FILE": os.path.join(BASE_DIR, "webpack-stats.json"),
        "POLL_INTERVAL": 0.1,
        "TIMEOUT": None,
        "IGNORE": [r".+\.hot-update\.+", r".+\.js\.map"],
    }
}

# configure a custom user model
AUTH_USER_MODEL = "users.User"

# Application definition
INSTALLED_APPS = (
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "social_django",
    "server_status",
    "oauth2_provider",
    "rest_framework",
    "anymail",
    "raven.contrib.django.raven_compat",
    # WAGTAIL
    "wagtail.contrib.forms",
    "wagtail.contrib.redirects",
    "wagtail.contrib.table_block",
    "wagtail.embeds",
    "wagtail.sites",
    "wagtail.users",
    "wagtail.snippets",
    "wagtail.documents",
    "wagtail.images",
    "wagtail.search",
    "wagtail.admin",
    "wagtail.core",
    "modelcluster",
    "taggit",
    # Put our apps after this point
    "mitxpro",
    "authentication",
    "courses",
    "mail",
    "users",
    "cms",
    "courseware",
    # must be after "users" to pick up custom user model
    "compat",
    "hijack",
    "hijack_admin",
    "ecommerce",
    "voucher",
)
# Only include the seed data app if this isn't running in prod
if ENVIRONMENT not in ("production", "prod"):
    INSTALLED_APPS += ("localdev.seed",)


DISABLE_WEBPACK_LOADER_STATS = get_bool("DISABLE_WEBPACK_LOADER_STATS", False)
if not DISABLE_WEBPACK_LOADER_STATS:
    INSTALLED_APPS += ("webpack_loader",)

MIDDLEWARE = (
    "django.middleware.security.SecurityMiddleware",
    "raven.contrib.django.raven_compat.middleware.SentryResponseErrorIdMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "oauth2_provider.middleware.OAuth2TokenMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "wagtail.core.middleware.SiteMiddleware",
    "wagtail.contrib.redirects.middleware.RedirectMiddleware",
    "mitxpro.middleware.BannerNotificationMiddleware",
)

# enable the nplusone profiler only in debug mode
if DEBUG:
    INSTALLED_APPS += ("nplusone.ext.django",)
    MIDDLEWARE += ("nplusone.ext.django.NPlusOneMiddleware",)

SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"

LOGIN_REDIRECT_URL = "/"
LOGIN_URL = "/login"
LOGIN_ERROR_URL = "/login"
LOGOUT_REDIRECT_URL = get_string("LOGOUT_REDIRECT_URL", "/")

ROOT_URLCONF = "mitxpro.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
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
            ]
        },
    }
]

WSGI_APPLICATION = "mitxpro.wsgi.application"


# Database
# https://docs.djangoproject.com/en/2.0/ref/settings/#databases
DEFAULT_DATABASE_CONFIG = dj_database_url.parse(
    get_string(
        "DATABASE_URL", "sqlite:///{0}".format(os.path.join(BASE_DIR, "db.sqlite3"))
    )
)
DEFAULT_DATABASE_CONFIG["CONN_MAX_AGE"] = get_int("MITXPRO_DB_CONN_MAX_AGE", 0)

if get_bool("MITXPRO_DB_DISABLE_SSL", False):
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

# social auth
AUTHENTICATION_BACKENDS = (
    "authentication.backends.micromasters.MicroMastersAuth",
    "social_core.backends.email.EmailAuth",
    "social_core.backends.saml.SAMLAuth",
    # the following needs to stay here to allow login of local users
    "django.contrib.auth.backends.ModelBackend",
    "guardian.backends.ObjectPermissionBackend",
)

SOCIAL_AUTH_LOGIN_ERROR_URL = "login"
SOCIAL_AUTH_ALLOWED_REDIRECT_HOSTS = [urlparse(SITE_BASE_URL).netloc]

# Micromasters backend settings
SOCIAL_AUTH_MICROMASTERS_LOGIN_URL = get_string(
    "SOCIAL_AUTH_MICROMASTERS_LOGIN_URL", None
)

# Email backend settings
SOCIAL_AUTH_EMAIL_FORM_URL = "login"
SOCIAL_AUTH_EMAIL_FORM_HTML = "login.html"

SOCIAL_AUTH_EMAIL_USER_FIELDS = ["username", "email", "name", "password"]


# Only validate emails for the email backend
SOCIAL_AUTH_EMAIL_FORCE_EMAIL_VALIDATION = True

# Configure social_core.pipeline.mail.mail_validation
SOCIAL_AUTH_EMAIL_VALIDATION_FUNCTION = "mail.verification_api.send_verification_email"
SOCIAL_AUTH_EMAIL_VALIDATION_URL = "/"

SOCIAL_AUTH_PIPELINE = (
    # Checks if an admin user attempts to login/register while hijacking another user.
    "authentication.pipeline.user.forbid_hijack",
    # Get the information we can about the user and return it in a simple
    # format to create the user instance later. On some cases the details are
    # already part of the auth response from the provider, but sometimes this
    # could hit a provider API.
    "social_core.pipeline.social_auth.social_details",
    # Get the social uid from whichever service we're authing thru. The uid is
    # the unique identifier of the given user in the provider.
    "social_core.pipeline.social_auth.social_uid",
    # Verifies that the current auth process is valid within the current
    # project, this is where emails and domains whitelists are applied (if
    # defined).
    "social_core.pipeline.social_auth.auth_allowed",
    # Checks if the current social-account is already associated in the site.
    "social_core.pipeline.social_auth.social_user",
    # Associates the current social details with another user account with the same email address.
    "social_core.pipeline.social_auth.associate_by_email",
    # validate an incoming email auth request
    "authentication.pipeline.user.validate_email_auth_request",
    # require a password and profile if they're not set
    "authentication.pipeline.user.validate_password",
    # Send a validation email to the user to verify its email address.
    # Disabled by default.
    "social_core.pipeline.mail.mail_validation",
    # Generate a username for the user
    # NOTE: needs to be right before create_user so nothing overrides the username
    "authentication.pipeline.user.get_username",
    # Create a user if one doesn't exist, and require a password and name
    "authentication.pipeline.user.create_user_via_email",
    # Create a profile
    "authentication.pipeline.user.create_profile",
    # Create the record that associates the social account with the user.
    "social_core.pipeline.social_auth.associate_user",
    # Populate the extra_data field in the social record with the values
    # specified by settings (and the default ones like access_token, etc).
    "social_core.pipeline.social_auth.load_extra_data",
    # Update the user record with any changed info from the auth service.
    "social_core.pipeline.user.user_details",
)

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.8/howto/static-files/

# Serve static files with dj-static
STATIC_URL = "/static/"
CLOUDFRONT_DIST = get_string("CLOUDFRONT_DIST", None)
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

# Request files from the webpack dev server
USE_WEBPACK_DEV_SERVER = get_bool("MITXPRO_USE_WEBPACK_DEV_SERVER", False)
WEBPACK_DEV_SERVER_HOST = get_string("WEBPACK_DEV_SERVER_HOST", "")
WEBPACK_DEV_SERVER_PORT = get_int("WEBPACK_DEV_SERVER_PORT", 8052)

# Important to define this so DEBUG works properly
INTERNAL_IPS = (get_string("HOST_IP", "127.0.0.1"),)

# Configure e-mail settings
EMAIL_BACKEND = get_string(
    "MITXPRO_EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend"
)
EMAIL_HOST = get_string("MITXPRO_EMAIL_HOST", "localhost")
EMAIL_PORT = get_int("MITXPRO_EMAIL_PORT", 25)
EMAIL_HOST_USER = get_string("MITXPRO_EMAIL_USER", "")
EMAIL_HOST_PASSWORD = get_string("MITXPRO_EMAIL_PASSWORD", "")
EMAIL_USE_TLS = get_bool("MITXPRO_EMAIL_TLS", False)
EMAIL_SUPPORT = get_string("MITXPRO_SUPPORT_EMAIL", "support@example.com")
DEFAULT_FROM_EMAIL = get_string("MITXPRO_FROM_EMAIL", "webmaster@localhost")

MAILGUN_SENDER_DOMAIN = get_string("MAILGUN_SENDER_DOMAIN", None)
MAILGUN_KEY = get_string("MAILGUN_KEY", None)
MAILGUN_BATCH_CHUNK_SIZE = get_int("MAILGUN_BATCH_CHUNK_SIZE", 1000)
MAILGUN_RECIPIENT_OVERRIDE = get_string("MAILGUN_RECIPIENT_OVERRIDE", None)
MAILGUN_FROM_EMAIL = get_string("MAILGUN_FROM_EMAIL", "no-reply@example.com")

NOTIFICATION_EMAIL_BACKEND = get_string(
    "MITXPRO_NOTIFICATION_EMAIL_BACKEND", "anymail.backends.mailgun.EmailBackend"
)

ANYMAIL = {
    "MAILGUN_API_KEY": MAILGUN_KEY,
    "MAILGUN_SENDER_DOMAIN": MAILGUN_SENDER_DOMAIN,
}

# e-mail configurable admins
ADMIN_EMAIL = get_string("MITXPRO_ADMIN_EMAIL", "")
if ADMIN_EMAIL != "":
    ADMINS = (("Admins", ADMIN_EMAIL),)
else:
    ADMINS = ()

# Logging configuration
LOG_LEVEL = get_string("MITXPRO_LOG_LEVEL", "INFO")
DJANGO_LOG_LEVEL = get_string("DJANGO_LOG_LEVEL", "INFO")
SENTRY_LOG_LEVEL = get_string("SENTRY_LOG_LEVEL", "ERROR")

# For logging to a remote syslog host
LOG_HOST = get_string("MITXPRO_LOG_HOST", "localhost")
LOG_HOST_PORT = get_int("MITXPRO_LOG_HOST_PORT", 514)

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
        "sentry": {
            "level": SENTRY_LOG_LEVEL,
            "class": "raven.contrib.django.raven_compat.handlers.SentryHandler",
            "formatter": "verbose",
        },
    },
    "loggers": {
        "django": {
            "propagate": True,
            "level": DJANGO_LOG_LEVEL,
            "handlers": ["console", "syslog", "sentry"],
        },
        "django.request": {
            "handlers": ["mail_admins"],
            "level": DJANGO_LOG_LEVEL,
            "propagate": True,
        },
        "raven": {"level": SENTRY_LOG_LEVEL, "handlers": []},
        "nplusone": {"handlers": ["console"], "level": "ERROR"},
    },
    "root": {"handlers": ["console", "syslog", "sentry"], "level": LOG_LEVEL},
}

# Sentry
SENTRY_CLIENT = "raven.contrib.django.raven_compat.DjangoClient"
RAVEN_CONFIG = {
    "dsn": get_string("SENTRY_DSN", ""),
    "environment": ENVIRONMENT,
    "release": VERSION,
}

# server-status
STATUS_TOKEN = get_string("STATUS_TOKEN", "")
HEALTH_CHECK = ["CELERY", "REDIS", "POSTGRES"]

GA_TRACKING_ID = get_string("GA_TRACKING_ID", "")
REACT_GA_DEBUG = get_bool("REACT_GA_DEBUG", False)

RECAPTCHA_SITE_KEY = get_string("RECAPTCHA_SITE_KEY", "")
RECAPTCHA_SECRET_KEY = get_string("RECAPTCHA_SECRET_KEY", "")

SITE_NAME = "MITxPRO"
WAGTAIL_SITE_NAME = SITE_NAME

MEDIA_ROOT = get_string("MEDIA_ROOT", "/var/media/")
MEDIA_URL = "/media/"
MITXPRO_USE_S3 = get_bool("MITXPRO_USE_S3", False)
AWS_ACCESS_KEY_ID = get_string("AWS_ACCESS_KEY_ID", False)
AWS_SECRET_ACCESS_KEY = get_string("AWS_SECRET_ACCESS_KEY", False)
AWS_STORAGE_BUCKET_NAME = get_string("AWS_STORAGE_BUCKET_NAME", False)
AWS_QUERYSTRING_AUTH = get_string("AWS_QUERYSTRING_AUTH", False)
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

# Celery
USE_CELERY = True
CELERY_BROKER_URL = get_string("CELERY_BROKER_URL", get_string("REDISCLOUD_URL", None))
CELERY_RESULT_BACKEND = get_string(
    "CELERY_RESULT_BACKEND", get_string("REDISCLOUD_URL", None)
)
CELERY_TASK_ALWAYS_EAGER = get_bool("CELERY_TASK_ALWAYS_EAGER", False)
CELERY_TASK_EAGER_PROPAGATES = get_bool("CELERY_TASK_EAGER_PROPAGATES", True)

CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TIMEZONE = "UTC"

# Hijack
HIJACK_ALLOW_GET_REQUESTS = True
HIJACK_LOGOUT_REDIRECT_URL = "/admin/users/user"
HIJACK_REGISTER_ADMIN = False

# django cache back-ends
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "local-in-memory-cache",
    },
    "redis": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": CELERY_BROKER_URL,
        "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
    },
}

AUTHENTICATION_BACKENDS = (
    "social_core.backends.email.EmailAuth",
    "oauth2_provider.backends.OAuth2Backend",
    "django.contrib.auth.backends.ModelBackend",
)

OAUTH2_PROVIDER = {
    # this is the list of available scopes
    "SCOPES": {
        "read": "Read scope",
        "write": "Write scope",
        "user:read": "Can read user and profile data",
    }
}
DEFAULT_SCOPES = ["user:read"]


# DRF configuration
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework.authentication.SessionAuthentication",
        "oauth2_provider.contrib.rest_framework.OAuth2Authentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "EXCEPTION_HANDLER": "mitxpro.exceptions.exception_handler",
    "TEST_REQUEST_DEFAULT_FORMAT": "json",
}

# Relative URL to be used by Djoser for the link in the password reset email
# (see: http://djoser.readthedocs.io/en/stable/settings.html#password-reset-confirm-url)
PASSWORD_RESET_CONFIRM_URL = "password_reset/confirm/{uid}/{token}/"

# Djoser library settings (see: http://djoser.readthedocs.io/en/stable/settings.html)
DJOSER = {
    "PASSWORD_RESET_CONFIRM_URL": PASSWORD_RESET_CONFIRM_URL,
    "SET_PASSWORD_RETYPE": False,
    "LOGOUT_ON_PASSWORD_CHANGE": False,
    "PASSWORD_RESET_CONFIRM_RETYPE": True,
    "PASSWORD_RESET_SHOW_EMAIL_NOT_FOUND": True,
    "EMAIL": {"password_reset": "authentication.views.CustomPasswordResetEmail"},
}

MITXPRO_OAUTH_PROVIDER = "mitxpro-oauth2"
OPENEDX_OAUTH_APP_NAME = get_string("OPENEDX_OAUTH_APP_NAME", "edx-oauth-app")
OPENEDX_API_BASE_URL = get_string("OPENEDX_API_BASE_URL", "http://edx.odl.local:18000")
OPENEDX_BASE_REDIRECT_URL = get_string(
    "OPENEDX_BASE_REDIRECT_URL", OPENEDX_API_BASE_URL
)
OPENEDX_TOKEN_EXPIRES_HOURS = get_int("OPENEDX_TOKEN_EXPIRES_HOURS", 1000)
OPENEDX_API_CLIENT_ID = get_string("OPENEDX_API_CLIENT_ID", None)
OPENEDX_API_CLIENT_SECRET = get_string("OPENEDX_API_CLIENT_SECRET", None)

MITXPRO_REGISTRATION_ACCESS_TOKEN = get_string(
    "MITXPRO_REGISTRATION_ACCESS_TOKEN", None
)


# features flags
def get_all_config_keys():
    """Returns all the configuration keys from both environment and configuration files"""
    return list(os.environ.keys())


MITXPRO_FEATURES_PREFIX = get_string("MITXPRO_FEATURES_PREFIX", "FEATURE_")
FEATURES = {
    key[len(MITXPRO_FEATURES_PREFIX) :]: get_any(key, None)
    for key in get_all_config_keys()
    if key.startswith(MITXPRO_FEATURES_PREFIX)
}

# django debug toolbar only in debug mode
if DEBUG:
    INSTALLED_APPS += ("debug_toolbar",)
    # it needs to be enabled before other middlewares
    MIDDLEWARE = ("debug_toolbar.middleware.DebugToolbarMiddleware",) + MIDDLEWARE

MANDATORY_SETTINGS = [
    "MAILGUN_SENDER_DOMAIN",
    "MAILGUN_KEY",
    "OPENEDX_OAUTH_APP_NAME",
    "OPENEDX_API_BASE_URL",
]

# Cybersource
CYBERSOURCE_ACCESS_KEY = get_string("CYBERSOURCE_ACCESS_KEY", None)
CYBERSOURCE_SECURITY_KEY = get_string("CYBERSOURCE_SECURITY_KEY", None)
CYBERSOURCE_SECURE_ACCEPTANCE_URL = get_string(
    "CYBERSOURCE_SECURE_ACCEPTANCE_URL", None
)
CYBERSOURCE_PROFILE_ID = get_string("CYBERSOURCE_PROFILE_ID", None)
CYBERSOURCE_REFERENCE_PREFIX = get_string("CYBERSOURCE_REFERENCE_PREFIX", None)

# Voucher keys for PDF parsing
VOUCHER_DOMESTIC_DATE_KEY = get_string("VOUCHER_DOMESTIC_DATE_KEY", None)
VOUCHER_DOMESTIC_EMPLOYEE_KEY = get_string("VOUCHER_DOMESTIC_EMPLOYEE_KEY", None)
VOUCHER_DOMESTIC_EMPLOYEE_ID_KEY = get_string("VOUCHER_DOMESTIC_EMPLOYEE_ID_KEY", None)
VOUCHER_DOMESTIC_KEY = get_string("VOUCHER_DOMESTIC_KEY", None)
VOUCHER_DOMESTIC_COURSE_KEY = get_string("VOUCHER_DOMESTIC_COURSE_KEY", None)
VOUCHER_DOMESTIC_CREDITS_KEY = get_string("VOUCHER_DOMESTIC_CREDITS_KEY", None)
VOUCHER_DOMESTIC_DATES_KEY = get_string("VOUCHER_DOMESTIC_DATES_KEY", None)
VOUCHER_DOMESTIC_AMOUNT_KEY = get_string("VOUCHER_DOMESTIC_AMOUNT_KEY", None)

VOUCHER_INTERNATIONAL_EMPLOYEE_KEY = get_string("VOUCHER_DOMESTIC_EMPLOYEE_KEY", None)
VOUCHER_INTERNATIONAL_PROGRAM_KEY = get_string(
    "VOUCHER_INTERNATIONAL_PROGRAM_KEY", None
)
VOUCHER_INTERNATIONAL_COURSE_KEY = get_string("VOUCHER_INTERNATIONAL_COURSE_KEY", None)
VOUCHER_INTERNATIONAL_SCHOOL_KEY = get_string("VOUCHER_INTERNATIONAL_SCHOOL_KEY", None)
VOUCHER_INTERNATIONAL_EMPLOYEE_ID_KEY = get_string(
    "VOUCHER_INTERNATIONAL_EMPLOYEE_ID_KEY", None
)
VOUCHER_INTERNATIONAL_AMOUNT_KEY = get_string("VOUCHER_INTERNATIONAL_AMOUNT_KEY", None)
VOUCHER_INTERNATIONAL_DATES_KEY = get_string("VOUCHER_INTERNATIONAL_DATES_KEY", None)
VOUCHER_INTERNATIONAL_COURSE_NAME_KEY = get_string(
    "VOUCHER_INTERNATIONAL_COURSE_NAME_KEY", None
)
VOUCHER_INTERNATIONAL_COURSE_NUMBER_KEY = get_string(
    "VOUCHER_INTERNATIONAL_COURSE_NUMBER_KEY", None
)
