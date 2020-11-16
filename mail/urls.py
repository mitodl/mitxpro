"""URL configurations for mail"""
from django.conf import settings
from django.conf.urls import url

from mail.views import EmailDebuggerView

urlpatterns = []

if settings.DEBUG and not settings.MITOL_MAIL_ENABLE_EMAIL_DEBUGGER:
    urlpatterns += [
        url(r"^__emaildebugger__/$", EmailDebuggerView.as_view(), name="email-debugger")
    ]
