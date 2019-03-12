"""URL configurations for mail"""
from django.conf import settings
from django.conf.urls import url

from mail.views import EmailDebuggerView

urlpatterns = []

if settings.DEBUG:
    urlpatterns += [
        url(r"^__emaildebugger__/$", EmailDebuggerView.as_view(), name="email-debugger")
    ]
