"""Endpoint URLs for sheets app"""
from django.urls import re_path

from sheets import views

urlpatterns = (
    re_path(
        r"^api/filewatch/",
        views.handle_file_push_notification,
        name="handle-file-push-notification",
    ),
)
