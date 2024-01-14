"""URL configurations for mail"""
from django.conf import settings
from django.urls import re_path

from mail.views import EmailDebuggerView

urlpatterns = []

if settings.DEBUG and not settings.MITOL_MAIL_ENABLE_EMAIL_DEBUGGER:
    urlpatterns += [
        re_path(
            r"^__emaildebugger__/$", EmailDebuggerView.as_view(), name="email-debugger"
        )
    ]
