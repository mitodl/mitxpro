"""Endpoint URLs for sheets app"""
from django.urls import re_path

from sheets import views

urlpatterns = (
    re_path(r"^sheets/admin/auth/", views.google_auth_view, name="google-auth-view"),
    re_path(
        r"^api/sheets/auth/", views.request_google_auth, name="request-google-auth"
    ),
    re_path(
        r"^api/sheets/auth-complete/",
        views.complete_google_auth,
        name="complete-google-auth",
    ),
    re_path(
        r"^api/sheets/filewatch/",
        views.handle_coupon_request_sheet_update,
        name="handle-coupon-request-sheet-update",
    ),
)
