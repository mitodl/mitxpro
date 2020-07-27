"""Endpoint URLs for sheets app"""
from django.urls import re_path
from django.conf import settings

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
if settings.FEATURES.get("COUPON_SHEETS_ALT_PROCESSING"):
    urlpatterns += [
        re_path(
            r"^api/sheets/coupon-requests/",
            views.process_request_sheet,
            name="process-request-sheet",
        ),
        re_path(
            r"^api/sheets/coupon-message-statuses/",
            views.update_assignment_delivery_statuses,
            name="update-assignment-delivery-statuses",
        ),
    ]
