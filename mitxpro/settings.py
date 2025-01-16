"""
Django settings for mitxpro.
"""

import logging
import os
import platform
from datetime import timedelta
from urllib.parse import urljoin, urlparse
from zoneinfo import ZoneInfo

import dj_database_url
from celery.schedules import crontab
from django.core.exceptions import ImproperlyConfigured
from mitol.common.envs import (
    env,
    get_bool,
    get_delimited_list,
    get_features,
    get_int,
    get_string,
    import_settings_modules,
)
from redbeat import RedBeatScheduler

from mitxpro.celery_utils import OffsettingSchedule
from mitxpro.sentry import init_sentry

VERSION = "0.171.0"

env.reset()

# import_settings_module, imports the default settings defined in ol-django-authentication app
import_settings_modules(
    "mitol.authentication.settings.djoser_settings",
    "mitol.common.settings.webpack",
    "mitol.digitalcredentials.settings",
)

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
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # noqa: PTH100, PTH120

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

ZENDESK_CONFIG = {
    "HELP_WIDGET_ENABLED": get_bool(
        name="ZENDESK_HELP_WIDGET_ENABLED",
        default=False,
        description="Enabled/disable state for Zendesk web help widget.",
    ),
    "HELP_WIDGET_KEY": get_string(
        name="ZENDESK_HELP_WIDGET_KEY",
        default="8ef9ef96-3317-40a9-8ef6-de0737503caa",
        description="Represents the key for Zendesk web help widget.",
    ),
}

WEBPACK_LOADER = {
    "DEFAULT": {
        "CACHE": not DEBUG,
        "BUNDLE_DIR_NAME": "bundles/",
        "STATS_FILE": os.path.join(BASE_DIR, "webpack-stats.json"),  # noqa: PTH118
        "POLL_INTERVAL": 0.1,
        "TIMEOUT": None,
        "IGNORE": [r".+\.hot-update\.+", r".+\.js\.map"],
    }
}

SITE_ID = get_string(
    name="MITXPRO_SITE_ID",
    default=1,
    description="The default site id for django sites framework",
)

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
    "wagtail.users",
    "wagtail.snippets",
    "wagtail.documents",
    "wagtail.images",
    "wagtail.search",
    "wagtail.admin",
    "wagtail",
    "wagtailmetadata",
    "modelcluster",
    "taggit",
    # django-robots
    "robots",
    # Put our apps after this point
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
    # ol-dango apps, must be after this project's apps for template precedence
    "mitol.hubspot_api.apps.HubspotApiApp",
    "mitol.common.apps.CommonApp",
    "mitol.digitalcredentials.apps.DigitalCredentialsApp",
    "mitol.mail.apps.MailApp",
    "mitol.oauth_toolkit_extensions.apps.OAuthToolkitExtensionsApp",
    "mitol.authentication.apps.TransitionalAuthenticationApp",
    "mitol.olposthog.apps.OlPosthog",
)
# Only include the seed data app if this isn't running in prod
if ENVIRONMENT not in ("production", "prod"):
    INSTALLED_APPS += ("localdev.seed",)


if not WEBPACK_DISABLE_LOADER_STATS:  # noqa: F821
    INSTALLED_APPS += ("webpack_loader",)

MIDDLEWARE = (
    "django.middleware.security.SecurityMiddleware",
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

# enable the nplusone profiler only in debug mode
if DEBUG:
    INSTALLED_APPS += (
        "nplusone.ext.django",
        "silk",
    )
    MIDDLEWARE += (
        "nplusone.ext.django.NPlusOneMiddleware",
        "silk.middleware.SilkyMiddleware",
    )

SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"

LOGIN_REDIRECT_URL = "/"
LOGIN_URL = "/signin"
LOGIN_ERROR_URL = "/signin"
LOGOUT_REDIRECT_URL = get_string(
    name="LOGOUT_REDIRECT_URL",
    default="/",
    description="Url to redirect to after logout, typically Open edX's own logout url",
)

ROOT_URLCONF = "mitxpro.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, "templates")],  # noqa: PTH118
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

WSGI_APPLICATION = "mitxpro.wsgi.application"


# Database
# https://docs.djangoproject.com/en/2.0/ref/settings/#databases
DEFAULT_DATABASE_CONFIG = dj_database_url.parse(
    get_string(
        name="DATABASE_URL",
        default="sqlite:///{}".format(os.path.join(BASE_DIR, "db.sqlite3")),  # noqa: PTH118
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


USE_TZ = True

# django-robots
ROBOTS_USE_HOST = False
ROBOTS_CACHE_TIMEOUT = get_int(
    name="ROBOTS_CACHE_TIMEOUT",
    default=60 * 60 * 24,
    description="How long the robots.txt file should be cached",
)

# profiling

SILKY_ANALYZE_QUERIES = True

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
    # validate the user's email either it is blocked or not.
    "authentication.pipeline.user.validate_email",
    # require a password and profile if they're not set
    "authentication.pipeline.user.validate_password",
    # Send a validation email to the user to verify its email address.
    # Disabled by default.
    "social_core.pipeline.mail.mail_validation",
    # Send the email address and hubspot cookie if it exists to hubspot_xpro.
    "authentication.pipeline.user.send_user_to_hubspot",
    # Generate a username for the user
    # NOTE: needs to be right before create_user so nothing overrides the username
    "authentication.pipeline.user.get_username",
    # Create a user if one doesn't exist, and require a password and name
    "authentication.pipeline.user.create_user_via_email",
    # verify the user against export compliance
    "authentication.pipeline.compliance.verify_exports_compliance",
    # Create the record that associates the social account with the user.
    "social_core.pipeline.social_auth.associate_user",
    # activate the user
    "authentication.pipeline.user.activate_user",
    # create the user's edx user and auth
    "authentication.pipeline.user.create_courseware_user",
    # Create a profile
    # NOTE: must be after all user records are created and the user is activated
    "authentication.pipeline.user.create_profile",
    # Populate the extra_data field in the social record with the values
    # specified by settings (and the default ones like access_token, etc).
    "social_core.pipeline.social_auth.load_extra_data",
    # Update the user record with any changed info from the auth service.
    "social_core.pipeline.user.user_details",
    # Sync user data with hubspot
    "authentication.pipeline.user.sync_user_to_hubspot",
)

AUTH_CHANGE_EMAIL_TTL_IN_MINUTES = get_int(
    name="AUTH_CHANGE_EMAIL_TTL_IN_MINUTES",
    default=60 * 24,
    description="Expiry time for a change email request, default is 1440 minutes(1 day)",
)

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
        f"https://{CLOUDFRONT_DIST}.cloudfront.net",
        STATIC_URL,
    )

STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
]

STATIC_ROOT = "staticfiles"
STATICFILES_DIRS = (os.path.join(BASE_DIR, "static"),)  # noqa: PTH118


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
ADMINS = (("Admins", ADMIN_EMAIL),) if ADMIN_EMAIL != "" else ()

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
            "format": (  # noqa: UP032
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

GTM_TRACKING_ID = get_string(
    name="GTM_TRACKING_ID", default="", description="Google Tag Manager container ID"
)
GA_TRACKING_ID = get_string(
    name="GA_TRACKING_ID", default="", description="Google analytics tracking ID"
)
REACT_GA_DEBUG = get_bool(
    name="REACT_GA_DEBUG",
    default=False,
    dev_only=True,
    description="Enable debug for react-ga, development only",
)

RECAPTCHA_SITE_KEY = get_string(
    name="RECAPTCHA_SITE_KEY", default="", description="The ReCaptcha site key"
)
RECAPTCHA_SECRET_KEY = get_string(
    name="RECAPTCHA_SECRET_KEY", default="", description="The ReCaptcha secret key"
)

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
        "You have enabled S3 support, but are missing one of "  # noqa: EM101
        "AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, or "
        "AWS_STORAGE_BUCKET_NAME"
    )
if MITXPRO_USE_S3:
    if CLOUDFRONT_DIST:
        AWS_S3_CUSTOM_DOMAIN = f"{CLOUDFRONT_DIST}.cloudfront.net"
    DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"

FEATURES = get_features()

CERTIFICATE_CREATION_DELAY_IN_HOURS = get_int(
    name="CERTIFICATE_CREATION_DELAY_IN_HOURS",
    default=48,
    description="The number of hours to delay automated certificate creation after a course run ends.",
)

# Redis
REDISCLOUD_URL = get_string(
    name="REDISCLOUD_URL", default=None, description="RedisCloud connection url"
)
if REDISCLOUD_URL is not None:
    _redis_url = REDISCLOUD_URL
else:
    _redis_url = get_string(
        name="REDIS_URL", default=None, description="Redis URL for non-production use"
    )

# Celery
USE_CELERY = True
CELERY_BROKER_URL = get_string(
    name="CELERY_BROKER_URL",
    default=_redis_url,
    description="Where celery should get tasks, default is Redis URL",
)
CELERY_RESULT_BACKEND = get_string(
    name="CELERY_RESULT_BACKEND",
    default=_redis_url,
    description="Where celery should put task results, default is Redis URL",
)
CELERY_BEAT_SCHEDULER = RedBeatScheduler
CELERY_REDBEAT_REDIS_URL = _redis_url
CELERY_TASK_ALWAYS_EAGER = get_bool(
    name="CELERY_TASK_ALWAYS_EAGER",
    default=False,
    dev_only=True,
    description="Enables eager execution of celery tasks, development only",
)
CELERY_TASK_EAGER_PROPAGATES = get_bool(
    name="CELERY_TASK_EAGER_PROPAGATES",
    default=True,
    description="Early executed tasks propagate exceptions",
)
CRON_COURSE_CERTIFICATES_HOURS = get_string(
    name="CRON_COURSE_CERTIFICATES_HOURS",
    default=0,
    description="'hours' value for the 'generate-course-certificate' scheduled task (defaults to midnight)",
)

CRON_COURSE_CERTIFICATES_DAYS = get_string(
    name="CRON_COURSE_CERTIFICATES_DAYS",
    default=None,
    description="'day_of_week' value for 'generate-course-certificate' scheduled task (default will run once a day).",
)
CRON_COURSERUN_SYNC_HOURS = get_string(
    name="CRON_COURSERUN_SYNC_HOURS",
    default=0,
    description="'hours' value for the 'sync-courseruns-data' scheduled task (defaults to midnight)",
)
CRON_COURSERUN_SYNC_DAYS = get_string(
    name="CRON_COURSERUN_SYNC_DAYS",
    default=None,
    description="'day_of_week' value for 'sync-courseruns-data' scheduled task (default will run once a day).",
)

CRON_EXTERNAL_COURSERUN_SYNC_HOURS = get_string(
    name="CRON_EXTERNAL_COURSERUN_SYNC_HOURS",
    default="0",
    description="'hours' value for the 'sync-external-course-runs' scheduled task (defaults to midnight)",
)
CRON_EXTERNAL_COURSERUN_SYNC_DAYS = get_string(
    name="CRON_EXTERNAL_COURSERUN_SYNC_DAYS",
    default=None,
    description="'day_of_week' value for 'sync-external-course-runs' scheduled task (default will run once a day).",
)

CRON_BASKET_DELETE_HOURS = get_string(
    name="CRON_BASKET_DELETE_HOURS",
    default=0,
    description="'hours' value for the 'delete-expired-baskets' scheduled task (defaults to midnight)",
)

CRON_BASKET_DELETE_DAYS = get_string(
    name="CRON_BASKET_DELETE_DAYS",
    default="*",
    description="'days' value for the 'delete-expired-baskets' scheduled task (defaults to everyday)",
)

BASKET_EXPIRY_DAYS = get_int(
    name="BASKET_EXPIRY_DAYS",
    default=15,
    description="Expiry life span of a basket in days",
)

CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TIMEZONE = "UTC"
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_SEND_SENT_EVENT = True

RETRY_FAILED_EDX_ENROLLMENT_FREQUENCY = get_int(
    name="RETRY_FAILED_EDX_ENROLLMENT_FREQUENCY",
    default=60 * 30,
    description="How many seconds between retrying failed edX enrollments",
)
REPAIR_COURSEWARE_USERS_FREQUENCY = get_int(
    name="REPAIR_COURSEWARE_USERS_FREQUENCY",
    default=60 * 30,
    description="How many seconds between repairing courseware records for faulty users",
)
REPAIR_COURSEWARE_USERS_OFFSET = int(REPAIR_COURSEWARE_USERS_FREQUENCY / 2)
DRIVE_WEBHOOK_EXPIRATION_MINUTES = get_int(
    name="DRIVE_WEBHOOK_EXPIRATION_MINUTES",
    default=60 * 24,
    description=(
        "The number of minutes after creation that a webhook (push notification) for a Drive "
        "file will expire (Google does not accept an expiration beyond 24 hours, and if the "
        "expiration is not provided via API, it defaults to 1 hour)."
    ),
)
DRIVE_WEBHOOK_RENEWAL_PERIOD_MINUTES = get_int(
    name="DRIVE_WEBHOOK_RENEWAL_PERIOD_MINUTES",
    default=60 * 3,
    description=(
        "The maximum time difference (in minutes) from the present time to a webhook expiration "
        "date to consider a webhook 'fresh', i.e.: not in need of renewal. If the time difference "
        "is less than this value, the webhook should be renewed."
    ),
)
DRIVE_WEBHOOK_ASSIGNMENT_WAIT = get_int(
    name="DRIVE_WEBHOOK_ASSIGNMENT_WAIT",
    default=60 * 5,
    description=(
        "The number of seconds to wait to process a coupon assignment sheet after we receive "
        "a webhook request from that sheet. The task to process the sheet is scheduled this many "
        "seconds in the future."
    ),
)
DRIVE_WEBHOOK_ASSIGNMENT_MAX_AGE_DAYS = get_int(
    name="DRIVE_WEBHOOK_ASSIGNMENT_MAX_AGE_DAYS",
    default=30,
    description=(
        "The number of days from the last update that a coupon assignment sheet should still be "
        "considered 'fresh', i.e.: should still be monitored for changes via webhook/file watch."
    ),
)
SHEETS_MONITORING_FREQUENCY = get_int(
    name="SHEETS_MONITORING_FREQUENCY",
    default=60 * 60 * 2,
    description="The frequency that the Drive folder should be checked for bulk coupon Sheets that need processing",
)
SHEETS_TASK_OFFSET = get_int(
    name="SHEETS_TASK_OFFSET",
    default=60 * 5,
    description="How many seconds to wait in between executing different Sheets tasks in series",
)

CELERY_BEAT_SCHEDULE = {
    "retry-failed-edx-enrollments": {
        "task": "courseware.tasks.retry_failed_edx_enrollments",
        "schedule": RETRY_FAILED_EDX_ENROLLMENT_FREQUENCY,
    },
    "repair-faulty-edx-users": {
        "task": "courseware.tasks.repair_faulty_courseware_users",
        "schedule": OffsettingSchedule(
            run_every=timedelta(seconds=REPAIR_COURSEWARE_USERS_FREQUENCY),
            offset=timedelta(seconds=REPAIR_COURSEWARE_USERS_OFFSET),
        ),
    },
    "generate-course-certificate": {
        "task": "courses.tasks.generate_course_certificates",
        "schedule": crontab(
            minute=0,
            hour=CRON_COURSE_CERTIFICATES_HOURS,
            day_of_week=CRON_COURSE_CERTIFICATES_DAYS or "*",
            day_of_month="*",
            month_of_year="*",
        ),
    },
    "sync-courseruns-data": {
        "task": "courses.tasks.sync_courseruns_data",
        "schedule": crontab(
            minute=0,
            hour=CRON_COURSERUN_SYNC_HOURS,
            day_of_week=CRON_COURSERUN_SYNC_DAYS or "*",
            day_of_month="*",
            month_of_year="*",
        ),
    },
    "sync-external-course-runs": {
        "task": "courses.tasks.task_sync_external_course_runs",
        "schedule": crontab(
            minute="0",
            hour=CRON_EXTERNAL_COURSERUN_SYNC_HOURS,
            day_of_week=CRON_EXTERNAL_COURSERUN_SYNC_DAYS or "*",
            day_of_month="*",
            month_of_year="*",
        ),
    },
    "delete-expired-baskets": {
        "task": "ecommerce.tasks.delete_expired_baskets",
        "schedule": crontab(
            minute=0,
            hour=CRON_BASKET_DELETE_HOURS,
            day_of_week=CRON_BASKET_DELETE_DAYS,
            day_of_month="*",
            month_of_year="*",
        ),
    },
}
if FEATURES.get("COUPON_SHEETS"):
    CELERY_BEAT_SCHEDULE["renew_all_file_watches"] = {
        "task": "sheets.tasks.renew_all_file_watches",
        "schedule": (
            DRIVE_WEBHOOK_EXPIRATION_MINUTES - DRIVE_WEBHOOK_RENEWAL_PERIOD_MINUTES
        )
        * 60,
    }
    alt_sheets_processing = FEATURES.get("COUPON_SHEETS_ALT_PROCESSING")
    if alt_sheets_processing:
        CELERY_BEAT_SCHEDULE.update(
            {
                "handle-coupon-request-sheet": {
                    "task": "sheets.tasks.handle_unprocessed_coupon_requests",
                    "schedule": SHEETS_MONITORING_FREQUENCY,
                }
            }
        )
    CELERY_BEAT_SCHEDULE.update(
        {
            "update-assignment-delivery-dates": {
                "task": "sheets.tasks.update_incomplete_assignment_delivery_statuses",
                "schedule": OffsettingSchedule(
                    run_every=timedelta(seconds=SHEETS_MONITORING_FREQUENCY),
                    offset=timedelta(
                        seconds=0 if not alt_sheets_processing else SHEETS_TASK_OFFSET
                    ),
                ),
            }
        }
    )

# Hijack
HIJACK_INSERT_BEFORE = "</body>"

# Wagtail
WAGTAIL_CACHE_BACKEND = get_string(
    name="WAGTAIL_CACHE_BACKEND",
    default="django_redis.cache.RedisCache",
    description="The caching backend to be used for Wagtail image renditions",
)
WAGTAIL_CACHE_URL = get_string(
    name="WAGTAIL_CACHE_URL",
    default=_redis_url,
    description="URL for Wagtail image renditions cache",
)
WAGTAIL_CACHE_MAX_ENTRIES = get_int(
    name="WAGTAIL_CACHE_MAX_ENTRIES",
    default=200,
    description="The maximum number of cache entries for Wagtail images",
)

WAGTAILADMIN_BASE_URL = SITE_BASE_URL

WAGTAILEMBEDS_FINDERS = [
    {"class": "cms.embeds.YouTubeEmbedFinder"},
    {"class": "wagtail.embeds.finders.oembed"},
]

BLOG_CACHE_TIMEOUT = get_int(
    name="BLOG_CACHE_TIMEOUT",
    default=60 * 60 * 24,
    description="How long the blog should be cached",
)

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
    "durable": {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": "durable_cache",
    },
}

AUTHENTICATION_BACKENDS = (
    "social_core.backends.email.EmailAuth",
    "oauth2_provider.backends.OAuth2Backend",
    "django.contrib.auth.backends.ModelBackend",
)


# required for migrations
OAUTH2_PROVIDER_ACCESS_TOKEN_MODEL = "oauth2_provider.AccessToken"  # noqa: S105
OAUTH2_PROVIDER_APPLICATION_MODEL = "oauth2_provider.Application"
OAUTH2_PROVIDER_REFRESH_TOKEN_MODEL = "oauth2_provider.RefreshToken"  # noqa: S105

OAUTH2_PROVIDER = {
    # this is the list of available scopes
    "SCOPES": {
        "read": "Read scope",
        "write": "Write scope",
        "user:read": "Can read user and profile data",
        "digitalcredentials": "Can read and write Digital Credentials data",
    },
    "DEFAULT_SCOPES": ["user:read"],
    "SCOPES_BACKEND_CLASS": "mitol.oauth_toolkit_extensions.backends.ApplicationAccessOrSettingsScopes",
    "ERROR_RESPONSE_WITH_SCOPES": DEBUG,
    "ALLOWED_REDIRECT_URI_SCHEMES": get_delimited_list(
        name="OAUTH2_PROVIDER_ALLOWED_REDIRECT_URI_SCHEMES",
        default=["http", "https"],
        description="List of schemes allowed for oauth2 redirect URIs",
    ),
}


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
PASSWORD_RESET_CONFIRM_URL = "password_reset/confirm/{uid}/{token}/"  # noqa: S105 # pragma: allowlist secret

# mitol-django-common
MITOL_COMMON_USER_FACTORY = "users.factories.UserFactory"

# mitol-django-mail
MITOL_MAIL_FROM_EMAIL = MAILGUN_FROM_EMAIL
MITOL_MAIL_REPLY_TO_ADDRESS = MITXPRO_REPLY_TO_ADDRESS
MITOL_MAIL_MESSAGE_CLASSES = ["courses.messages.DigitalCredentialAvailableMessage"]
MITOL_MAIL_RECIPIENT_OVERRIDE = MAILGUN_RECIPIENT_OVERRIDE
MITOL_MAIL_FORMAT_RECIPIENT_FUNC = "users.utils.format_recipient"
MITOL_MAIL_ENABLE_EMAIL_DEBUGGER = get_bool(  # NOTE: this will override the legacy mail debugger defined in this project
    name="MITOL_MAIL_ENABLE_EMAIL_DEBUGGER",
    default=False,
    description="Enable the mitol-mail email debugger",
    dev_only=True,
)

# mitol-django-digital-credentials
MITOL_DIGITAL_CREDENTIALS_BUILD_CREDENTIAL_FUNC = (
    "courses.credentials.build_digital_credential"
)

# mitol-django-authenticaton
MITOL_AUTHENTICATION_FROM_EMAIL = MAILGUN_FROM_EMAIL
MITOL_AUTHENTICATION_REPLY_TO_EMAIL = MITXPRO_REPLY_TO_ADDRESS


OPENEDX_OAUTH_PROVIDER = get_string(
    name="OPENEDX_OAUTH_PROVIDER",
    default="mitxpro-oauth2",
    description="Social auth oauth provider backend name",
)

OPENEDX_SOCIAL_LOGIN_PATH = get_string(
    name="OPENEDX_SOCIAL_LOGIN_PATH",
    default="/auth/login/mitxpro-oauth2/?auth_entry=login",
    description="Open edX social auth login url",
)

OPENEDX_OAUTH_APP_NAME = get_string(
    name="OPENEDX_OAUTH_APP_NAME",
    default="edx-oauth-app",
    required=True,
    description="The 'name' value for the Open edX OAuth Application",
)
OPENEDX_API_BASE_URL = get_string(
    name="OPENEDX_API_BASE_URL",
    default="http://edx.odl.local:18000",
    description="The base URL for the Open edX API",
    required=True,
)
OPENEDX_BASE_REDIRECT_URL = get_string(
    name="OPENEDX_BASE_REDIRECT_URL",
    default=OPENEDX_API_BASE_URL,
    description="The base redirect URL for an OAuth Application for the Open edX API",
)
OPENEDX_TOKEN_EXPIRES_HOURS = get_int(
    name="OPENEDX_TOKEN_EXPIRES_HOURS",
    default=1000,
    description="The number of hours until an access token for the Open edX API expires",
)
OPENEDX_API_CLIENT_ID = get_string(
    name="OPENEDX_API_CLIENT_ID",
    default=None,
    description="The OAuth2 client id to connect to Open edX with",
    required=True,
)
OPENEDX_API_CLIENT_SECRET = get_string(
    name="OPENEDX_API_CLIENT_SECRET",
    default=None,
    description="The OAuth2 client secret to connect to Open edX with",
    required=True,
)

MITXPRO_REGISTRATION_ACCESS_TOKEN = get_string(
    name="MITXPRO_REGISTRATION_ACCESS_TOKEN",
    default=None,
    description="Access token to secure Open edX registration API with",
)

OPENEDX_SERVICE_WORKER_API_TOKEN = get_string(
    name="OPENEDX_SERVICE_WORKER_API_TOKEN",
    default=None,
    description="Active access token with staff level permissions to use with OpenEdX API client for service tasks",
)
OPENEDX_SERVICE_WORKER_USERNAME = get_string(
    name="OPENEDX_SERVICE_WORKER_USERNAME",
    default=None,
    description="Username of the user whose token has been set in OPENEDX_SERVICE_WORKER_API_TOKEN",
)
EDX_API_CLIENT_TIMEOUT = get_int(
    name="EDX_API_CLIENT_TIMEOUT",
    default=60,
    description="Timeout (in seconds) for requests made via the edX API client",
)

EXTERNAL_COURSE_SYNC_API_KEY = get_string(
    name="EXTERNAL_COURSE_SYNC_API_KEY",
    default=None,
    description="The API Key for external course sync API",
    required=True,
)
EXTERNAL_COURSE_SYNC_API_BASE_URL = get_string(
    name="EXTERNAL_COURSE_SYNC_API_BASE_URL",
    default="https://mit-xpro.emeritus-analytics.io/",
    description="Base API URL for external course sync API",
)
EXTERNAL_COURSE_SYNC_API_REQUEST_TIMEOUT = get_int(
    name="EXTERNAL_COURSE_SYNC_API_REQUEST_TIMEOUT",
    default=60,
    description="API request timeout for external course sync APIs in seconds",
)

# django debug toolbar only in debug mode
if DEBUG:
    INSTALLED_APPS += ("debug_toolbar",)
    # it needs to be enabled before other middlewares
    MIDDLEWARE = ("debug_toolbar.middleware.DebugToolbarMiddleware",) + MIDDLEWARE  # noqa: RUF005

# Cybersource
CYBERSOURCE_ACCESS_KEY = get_string(
    name="CYBERSOURCE_ACCESS_KEY", default=None, description="CyberSource Access Key"
)
CYBERSOURCE_SECURITY_KEY = get_string(
    name="CYBERSOURCE_SECURITY_KEY", default=None, description="CyberSource API key"
)
CYBERSOURCE_SECURE_ACCEPTANCE_URL = get_string(
    name="CYBERSOURCE_SECURE_ACCEPTANCE_URL",
    default=None,
    description="CyberSource API endpoint",
)
CYBERSOURCE_PROFILE_ID = get_string(
    name="CYBERSOURCE_PROFILE_ID", default=None, description="CyberSource Profile ID"
)
CYBERSOURCE_WSDL_URL = get_string(
    name="CYBERSOURCE_WSDL_URL",
    default=None,
    description="The URL to the cybersource WSDL",
)
CYBERSOURCE_MERCHANT_ID = get_string(
    name="CYBERSOURCE_MERCHANT_ID",
    default=None,
    description="The cybersource merchant id",
)
CYBERSOURCE_TRANSACTION_KEY = get_string(
    name="CYBERSOURCE_TRANSACTION_KEY",
    default=None,
    description="The cybersource transaction key",
)
CYBERSOURCE_INQUIRY_LOG_NACL_ENCRYPTION_KEY = get_string(
    name="CYBERSOURCE_INQUIRY_LOG_NACL_ENCRYPTION_KEY",
    default=None,
    description="The public key to encrypt export results with for our own security purposes. Should be a base64 encoded NaCl public key.",
)
CYBERSOURCE_EXPORT_SERVICE_ADDRESS_OPERATOR = get_string(
    name="CYBERSOURCE_EXPORT_SERVICE_ADDRESS_OPERATOR",
    default="AND",
    description="Whether just the name or the name and address should be used in exports verification. Refer to Cybersource docs.",
)
CYBERSOURCE_EXPORT_SERVICE_ADDRESS_WEIGHT = get_string(
    name="CYBERSOURCE_EXPORT_SERVICE_ADDRESS_WEIGHT",
    default="high",
    description="The weight of the address in determining whether a user passes exports checks. Refer to Cybersource docs.",
)
CYBERSOURCE_EXPORT_SERVICE_NAME_WEIGHT = get_string(
    name="CYBERSOURCE_EXPORT_SERVICE_NAME_WEIGHT",
    default="high",
    description="The weight of the name in determining whether a user passes exports checks. Refer to Cybersource docs.",
)

CYBERSOURCE_EXPORT_SERVICE_SANCTIONS_LISTS = get_string(
    name="CYBERSOURCE_EXPORT_SERVICE_SANCTIONS_LISTS",
    default=None,
    description="Additional sanctions lists to validate for exports. Refer to Cybersource docs.",
)

# Voucher keys for PDF parsing
VOUCHER_DOMESTIC_EMPLOYEE_KEY = get_string(
    name="VOUCHER_DOMESTIC_EMPLOYEE_KEY",
    default="UNIQUE02",
    description="Employee key for domestic vouchers",
)
VOUCHER_DOMESTIC_EMPLOYEE_ID_KEY = get_string(
    name="VOUCHER_DOMESTIC_EMPLOYEE_ID_KEY",
    default="UNIQUE03",
    description="Voucher employee key ID for domestic vouchers",
)
VOUCHER_DOMESTIC_KEY = get_string(
    name="VOUCHER_DOMESTIC_KEY",
    default="UNIQUE04",
    description="Voucher key for domestic vouchers",
)
VOUCHER_DOMESTIC_COURSE_KEY = get_string(
    name="VOUCHER_DOMESTIC_COURSE_KEY",
    default="UNIQUE05",
    description="Course key for domestic vouchers",
)
VOUCHER_DOMESTIC_CREDITS_KEY = get_string(
    name="VOUCHER_DOMESTIC_CREDITS_KEY",
    default="UNIQUE06",
    description="Credits key for domestic vouchers",
)
VOUCHER_DOMESTIC_DATES_KEY = get_string(
    name="VOUCHER_DOMESTIC_DATES_KEY",
    default="UNIQUE07",
    description="Dates key for domestic vouchers",
)
VOUCHER_DOMESTIC_AMOUNT_KEY = get_string(
    name="VOUCHER_DOMESTIC_AMOUNT_KEY",
    default="UNIQUE08",
    description="Amount key for domestic vouchers",
)

VOUCHER_INTERNATIONAL_EMPLOYEE_KEY = get_string(
    name="VOUCHER_INTERNATIONAL_EMPLOYEE_KEY",
    default="UNIQUE09",
    description="Employee key for international vouchers",
)
VOUCHER_INTERNATIONAL_EMPLOYEE_ID_KEY = get_string(
    name="VOUCHER_INTERNATIONAL_EMPLOYEE_ID_KEY",
    default="UNIQUE13",
    description="Voucher employee key ID for international vouchers",
)
VOUCHER_INTERNATIONAL_DATES_KEY = get_string(
    name="VOUCHER_INTERNATIONAL_DATES_KEY",
    default="UNIQUE15",
    description="Dates key for international vouchers",
)
VOUCHER_INTERNATIONAL_COURSE_NAME_KEY = get_string(
    name="VOUCHER_INTERNATIONAL_COURSE_NAME_KEY",
    default="UNIQUE16",
    description="Course name key for international vouchers",
)
VOUCHER_INTERNATIONAL_COURSE_NUMBER_KEY = get_string(
    name="VOUCHER_INTERNATIONAL_COURSE_NUMBER_KEY",
    default="UNIQUE17",
    description="Course number key for international vouchers",
)

VOUCHER_COMPANY_ID = get_int(
    name="VOUCHER_COMPANY_ID", default="1", description="Company ID for vouchers"
)

# PostHog related settings

POSTHOG_ENABLED = get_bool(
    name="POSTHOG_ENABLED",
    default=False,
    description="Whether PostHog is enabled",
)

POSTHOG_PROJECT_API_KEY = get_string(
    name="POSTHOG_PROJECT_API_KEY",
    default="",
    description="API token to communicate with PostHog",
)

POSTHOG_API_HOST = get_string(
    name="POSTHOG_API_HOST",
    default="",
    description="API host for PostHog",
)
POSTHOG_FEATURE_FLAG_REQUEST_TIMEOUT_MS = get_int(
    name="POSTHOG_FEATURE_FLAG_REQUEST_TIMEOUT_MS",
    default=3000,
    description="Timeout(MS) for PostHog feature flag requests.",
)

POSTHOG_MAX_RETRIES = get_int(
    name="POSTHOG_MAX_RETRIES",
    default=3,
    description="Number of times that requests to PostHog should be retried after failing.",
)

# Hubspot sync settings
MITOL_HUBSPOT_API_PRIVATE_TOKEN = get_string(
    name="MITOL_HUBSPOT_API_PRIVATE_TOKEN",
    default=None,
    description="Hubspot private token to authenticate with API",
)
MITOL_HUBSPOT_API_RETRIES = get_int(
    name="MITOL_HUBSPOT_API_RETRIES",
    default=3,
    description="Number of times to retry a failed hubspot API request",
)
MITOL_HUBSPOT_API_ID_PREFIX = get_string(
    name="MITOL_HUBSPOT_API_ID_PREFIX",
    default="XPRO",
    description="The prefix to use for hubspot unique_app_id field values",
)
HUBSPOT_PIPELINE_ID = get_string(
    name="HUBSPOT_PIPELINE_ID",
    default="default",
    description="Hubspot ID for the ecommerce pipeline",
)
HUBSPOT_MAX_CONCURRENT_TASKS = get_int(
    name="HUBSPOT_MAX_CONCURRENT_TASKS",
    default=4,
    description="Max number of concurrent Hubspot tasks to run",
)
HUBSPOT_TASK_DELAY = get_int(
    name="HUBSPOT_TASK_DELAY",
    default=1000,
    description="Number of milliseconds to wait between consecutive Hubspot calls",
)
HUBSPOT_CONFIG = {
    "HUBSPOT_NEW_COURSES_FORM_GUID": get_string(
        name="HUBSPOT_NEW_COURSES_FORM_GUID",
        default="",
        description="Form guid over hub spot for new courses email subscription form.",
    ),
    "HUBSPOT_FOOTER_FORM_GUID": get_string(
        name="HUBSPOT_FOOTER_FORM_GUID",
        default="",
        description="Form guid over hub spot for footer block.",
    ),
    "HUBSPOT_PORTAL_ID": get_string(
        name="HUBSPOT_PORTAL_ID", default="", description="Hub spot portal id."
    ),
    "HUBSPOT_CREATE_USER_FORM_ID": get_string(
        name="HUBSPOT_CREATE_USER_FORM_ID",
        default=None,
        description="Form ID for Hubspot Forms API",
    ),
    "HUBSPOT_ENTERPRISE_PAGE_FORM_ID": get_string(
        name="HUBSPOT_ENTERPRISE_PAGE_FORM_ID",
        default=None,
        description="Form ID for Hubspot for Enterprise Page",
    ),
}

# Sheets settings
DRIVE_SERVICE_ACCOUNT_CREDS = get_string(
    name="DRIVE_SERVICE_ACCOUNT_CREDS",
    default=None,
    description="The contents of the Service Account credentials JSON to use for Google API auth",
)
DRIVE_CLIENT_ID = get_string(
    name="DRIVE_CLIENT_ID",
    default=None,
    description="Client ID from Google API credentials",
)
DRIVE_CLIENT_SECRET = get_string(
    name="DRIVE_CLIENT_SECRET",
    default=None,
    description="Client secret from Google API credentials",
)
DRIVE_API_PROJECT_ID = get_string(
    name="DRIVE_API_PROJECT_ID",
    default=None,
    description="ID for the Google API project where the credentials were created",
)
DRIVE_WEBHOOK_CHANNEL_ID = get_string(
    name="DRIVE_WEBHOOK_CHANNEL_ID",
    default="mitxpro-sheets-app",
    description="Channel ID to use for requests to get push notifications for file changes",
)
DRIVE_SHARED_ID = get_string(
    name="DRIVE_SHARED_ID",
    default=None,
    description="ID of the Shared Drive (a.k.a. Team Drive). This is equal to the top-level folder ID.",
)
DRIVE_OUTPUT_FOLDER_ID = get_string(
    name="DRIVE_OUTPUT_FOLDER_ID",
    default=None,
    description="ID of the Drive folder where newly created Sheets should be kept",
)
COUPON_REQUEST_SHEET_ID = get_string(
    name="COUPON_REQUEST_SHEET_ID",
    default=None,
    description="ID of the Google Sheet that contains requests for coupons",
)
ENROLLMENT_CHANGE_SHEET_ID = get_string(
    name="ENROLLMENT_CHANGE_SHEET_ID",
    default=None,
    description=(
        "ID of the Google Sheet that contains the enrollment change request worksheets (refunds, transfers, etc)"
    ),
)
REFUND_REQUEST_WORKSHEET_ID = get_string(
    name="REFUND_REQUEST_WORKSHEET_ID",
    default="0",
    description=(
        "ID of the worksheet within the enrollment change request spreadsheet that contains enrollment refund requests"
    ),
)
DEFERRAL_REQUEST_WORKSHEET_ID = get_string(
    name="DEFERRAL_REQUEST_WORKSHEET_ID",
    default=None,
    description=(
        "ID of the worksheet within the enrollment change request spreadsheet that contains "
        "enrollment deferral requests"
    ),
)
GOOGLE_DOMAIN_VERIFICATION_TAG_VALUE = get_string(
    name="GOOGLE_DOMAIN_VERIFICATION_TAG_VALUE",
    default=None,
    description="The value of the meta tag used by Google to verify the owner of a domain (used for enabling push notifications)",
)
SHEETS_ADMIN_EMAILS = get_delimited_list(
    name="SHEETS_ADMIN_EMAILS",
    default=[],
    description="Comma-separated list of emails for users that should be added as an editor for all newly created Sheets",
)
SHEETS_DATE_FORMAT = get_string(
    name="SHEETS_DATE_FORMAT",
    default="%m/%d/%Y %H:%M:%S",
    description="Python strptime format for datetime columns in enrollment management spreadsheets",
)
SHEETS_DATE_ONLY_FORMAT = get_string(
    name="SHEETS_DATE_ONLY_FORMAT",
    default="%m/%d/%Y",
    description="Python strptime format for date columns (no time) in enrollment management spreadsheets",
)
_sheets_date_timezone = get_string(
    name="SHEETS_DATE_TIMEZONE",
    default="UTC",
    description=(
        "The name of the timezone that should be assumed for date/time values in spreadsheets. "
        "Choose from a value in the TZ database (https://en.wikipedia.org/wiki/List_of_tz_database_time_zones)."
    ),
)
SHEETS_DATE_TIMEZONE = ZoneInfo(_sheets_date_timezone)

SHEETS_REFUND_FIRST_ROW = get_int(
    name="SHEETS_REFUND_FIRST_ROW",
    default=4,
    description=(
        "The first row (as it appears in the spreadsheet) of data that our scripts should consider "
        "processing in the refund request spreadsheet"
    ),
)
SHEETS_DEFERRAL_FIRST_ROW = get_int(
    name="SHEETS_DEFERRAL_FIRST_ROW",
    default=5,
    description=(
        "The first row (as it appears in the spreadsheet) of data that our scripts should consider "
        "processing in the deferral request spreadsheet"
    ),
)
# Specify the zero-based index of certain request sheet columns
SHEETS_REQ_EMAIL_COL = 7
SHEETS_REQ_PROCESSED_COL = 8
SHEETS_REQ_ERROR_COL = 9
SHEETS_REQ_CALCULATED_COLUMNS = {
    SHEETS_REQ_EMAIL_COL,
    SHEETS_REQ_PROCESSED_COL,
    SHEETS_REQ_ERROR_COL,
}
# Calculate the column letters in the spreadsheet based on those indices
_uppercase_a_ord = ord("A")
SHEETS_REQ_PROCESSED_COL_LETTER = chr(SHEETS_REQ_PROCESSED_COL + _uppercase_a_ord)
SHEETS_REQ_ERROR_COL_LETTER = chr(SHEETS_REQ_ERROR_COL + _uppercase_a_ord)

SHEETS_REFUND_PROCESSOR_COL = get_int(
    name="SHEETS_REFUND_PROCESSOR_COL",
    default=11,
    description=(
        "The zero-based index of the enrollment change sheet column that contains the user that processed the row"
    ),
)
SHEETS_REFUND_COMPLETED_DATE_COL = get_int(
    name="SHEETS_REFUND_COMPLETED_DATE_COL",
    default=12,
    description=(
        "The zero-based index of the enrollment change sheet column that contains the row completion date"
    ),
)
SHEETS_REFUND_ERROR_COL = get_int(
    name="SHEETS_REFUND_ERROR_COL",
    default=13,
    description=(
        "The zero-based index of the enrollment change sheet column that contains row processing error messages"
    ),
)
SHEETS_REFUND_SKIP_ROW_COL = get_int(
    name="SHEETS_REFUND_SKIP_ROW_COL",
    default=14,
    description=(
        "The zero-based index of the enrollment change sheet column that indicates whether the row should be skipped"
    ),
)

# Digital Credentials
DIGITAL_CREDENTIALS_DEEP_LINK_URL = get_string(
    name="DIGITAL_CREDENTIALS_DEEP_LINK_URL",
    default=None,
    description="URL at which to deep link the learner to for the digital credentials wallet",
)
DIGITAL_CREDENTIALS_ISSUER_ID = get_string(
    name="DIGITAL_CREDENTIALS_ISSUER_ID",
    default=None,
    description="Issuer identifier for digital credentials",
)
DIGITAL_CREDENTIALS_VERIFICATION_METHOD = get_string(
    name="DIGITAL_CREDENTIALS_VERIFICATION_METHOD",
    default=None,
    description="Verification method for digital credentials",
)
# TODO: This setting is meant to be temporary and it should be removed once we decide to support digital credentials  # noqa: FIX002, TD002, TD003
#  for all courses/programs.
DIGITAL_CREDENTIALS_SUPPORTED_RUNS = get_delimited_list(
    name="DIGITAL_CREDENTIALS_SUPPORTED_RUNS",
    default=[],
    description="Comma separated string of course/program runs/Ids that support digital credentials",
)

DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

# Force the country determination code to use the user's profile only
# This is for local testing, since your IP won't belong to a country
ECOMMERCE_FORCE_PROFILE_COUNTRY = get_bool(
    name="ECOMMERCE_FORCE_PROFILE_COUNTRY",
    default=False,
    description="Force the country determination to be done with the user profile only",
)
