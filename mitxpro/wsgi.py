"""
WSGI config for xpro django app.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.8/howto/deployment/wsgi/

Based on https://gist.github.com/rbarrois/044b2d9f7052a6542f7a3d79695d64c6
"""
import io
import logging
import os
import sys
import wsgiref.util

import uwsgidecorators


# pylint: disable=global-statement,unused-argument

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mitxpro.settings")


DJANGO_WARMUP_URL = os.environ.get("DJANGO_WARMUP_URL", "/")  # Default to home page

log = logging.getLogger()


@uwsgidecorators.postfork
def setup_postfork():
    """Ensure each worker is warm after fork as well."""
    # Warmup as well
    warmup_django()


def warmup_django(close_connections=False):
    """Warm up the lazy django app"""
    from django.conf import settings

    global application

    log.debug("warming up")

    if settings.ALLOWED_HOSTS:
        host = settings.ALLOWED_HOSTS[0].replace("*", "warmup")
    else:
        host = "localhost"
    env = {
        "REQUEST_METHOD": "GET",
        "PATH_INFO": DJANGO_WARMUP_URL,
        "SERVER_NAME": host,
        "wsgi.error": sys.stderr,
    }
    # Setup the whole wsgi standard headers we do not care about.
    wsgiref.util.setup_testing_defaults(env)

    def start_response(status, response_headers, exc_info=None):
        """Start the warmup response"""
        log.debug("starting warmup response")
        assert status == "200 OK"
        fake_socket = io.BytesIO()
        return fake_socket

    application(env, start_response)

    if close_connections:
        # Close connections before forking
        from django.db import connections

        log.debug("Closing connection")
        for conn in connections.all():
            conn.close()


def get_wsgi_application():
    """Call the standard wsgi.get_wsgi_application() and then the warmup function"""
    from django.core import wsgi

    global application
    application = wsgi.get_wsgi_application()
    if DJANGO_WARMUP_URL:
        warmup_django(close_connections=True)
    return application


application = get_wsgi_application()
