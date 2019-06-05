"""
Voucher URL patterns
"""
from django.urls import path
from voucher import views

urlpatterns = [
    path("upload/", views.UploadVoucherFormView.as_view(), name="upload"),
    path("resubmit/", views.resubmit, name="resubmit"),
    path("redeemed/", views.redeemed, name="redeemed"),
    path("enroll/", views.EnrollView.as_view(), name="enroll"),
]
