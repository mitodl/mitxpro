"""
WSGI config for ui app.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.8/howto/deployment/wsgi/
"""
import io
import os
import sys
import wsgiref.util

import uwsgidecorators


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mitxpro.settings")


DJANGO_WARMUP_URL = os.environ.get('DJANGO_WARMUP_URL', '/')

application = None


@uwsgidecorators.postfork
def setup_postfork():
    """Ensure each worker is warm *after* fork as well."""
    # Warmup as well
    warmup_django()


def warmup_django(close_connections=False):
    from django.conf import settings
    print("WARMUP")
    if settings.ALLOWED_HOSTS:
        host = settings.ALLOWED_HOSTS[0].replace('*', 'warmup')
    else:
        host = 'localhost'
    env = {
        'REQUEST_METHOD': 'GET',
        'PATH_INFO': DJANGO_WARMUP_URL,
        'SERVER_NAME': host,
        'wsgi.error': sys.stderr,
    }
    # Setup the whole wsgi standard headers we do not care about.
    wsgiref.util.setup_testing_defaults(env)

    def start_response(status, response_headers, exc_info=None):
        print("START RESPONSE")
        assert status == "200 OK"
        fake_socket = io.BytesIO()
        return fake_socket

    global application
    application(env, start_response)

    if close_connections:
        # Close connections before forking
        print("CLOSE CONNECTION")
        from django.db import connections
        for conn in connections.all():
            conn.close()


def get_wsgi_application():
    from django.core import wsgi
    global application
    application = wsgi.get_wsgi_application()
    if DJANGO_WARMUP_URL:
        warmup_django(close_connections=True)
    return application


application = get_wsgi_application()
