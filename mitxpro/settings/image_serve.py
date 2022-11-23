"""
Django settings for mitxpro image serving app
"""

from mitxpro.settings.shared import *

INSTALLED_APPS += (
    # minimum applications needed to get the server stood up
    "affiliate",
    "users",
    # necessary because of imports
    "hijack",
    "hijack_admin",
)


ROOT_URLCONF = "mitxpro.urls.image_serve"

WSGI_APPLICATION = "mitxpro.wsgi.application"
