"""Endpoint URLs for sheets app"""
from django.urls import re_path

from sheets import views

urlpatterns = [
    re_path(r"^sheets/admin/", views.sheets_admin_view, name="sheets-admin-view"),
    re_path(
        r"^api/sheets/auth/", views.request_google_auth, name="request-google-auth"
    ),
    re_path(
        r"^api/sheets/auth-complete/",
        views.complete_google_auth,
        name="complete-google-auth",
    ),
    re_path(
        r"^api/sheets/watch/",
        views.handle_watched_sheet_update,
        name="handle-watched-sheet-update",
    ),
]
