"""
Voucher views
"""
import json
from datetime import datetime
import logging

import pytz
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views.generic import FormView
from django.views.generic.base import View
from django.contrib import messages


from ecommerce.utils import make_checkout_url
from ecommerce.models import Coupon, Product
from mitxpro.views import get_base_context
from voucher.forms import UploadVoucherForm, VOUCHER_PARSE_ERROR
from voucher.models import Voucher
from voucher.utils import (
    get_current_voucher,
    get_valid_voucher_coupons_version,
    get_eligible_coupon_choices,
)

log = logging.getLogger()


class UploadVoucherFormView(LoginRequiredMixin, FormView):
    """
    UploadVoucherFormView displays the voucher upload form and handles its submission
    """

    template_name = "upload.html"
    form_class = UploadVoucherForm

    def form_valid(self, form):
        """
        Get or create voucher for the user using the parsed voucher values
        """
        values = form.cleaned_data["voucher"]
        user = self.request.user
        # Check if a matching voucher already exists
        old_voucher = Voucher.objects.filter(
            employee_id=values.get("employee_id"),
            employee_name=values.get("employee_name"),
            course_start_date_input=values.get("course_start_date_input"),
            course_id_input=values.get("course_id_input"),
            course_title_input=values.get("course_title_input"),
        ).last()
        # If a voucher exists, make sure it is the same user, and update the upload time
        if old_voucher:
            if old_voucher.user != user:
                log.error(
                    "%s uploaded a voucher previously uploaded by %s",
                    user.username,
                    old_voucher.user.username,
                )
                return redirect("voucher:resubmit")
            voucher = old_voucher
            voucher.uploaded = datetime.now(tz=pytz.UTC)
            voucher.save()
        else:
            Voucher.objects.create(**values, user=user)

        return redirect("voucher:enroll")

    def form_invalid(self, form):
        """
        Redirect to the resubmit page if the voucher couldn't be parsed
        """
        if VOUCHER_PARSE_ERROR in form.errors["voucher"]:
            log.error(
                "Voucher uploaded by %s could not be parsed", self.request.user.username
            )
            return redirect(reverse("voucher:resubmit"))
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), **get_base_context(self.request)}


class EnrollView(LoginRequiredMixin, View):
    """
    EnrollView checks the status of the voucher and looks for valid course runs to redeem it for

    On a POST, it redirects to the enrollment URL based on the submitted CouponEligibility object's product and
    coupon_code
    """

    def get(self, request):
        """
        If voucher is not redeemed and valid coupons exist for course runs matching the input strings,
        render the enroll form with CouponEligibility objects as choices.
        """
        voucher = get_current_voucher(self.request.user)
        if voucher is None:
            return redirect("voucher:upload")
        elif voucher.is_redeemed():
            return redirect("voucher:redeemed")
        eligible_choices = get_eligible_coupon_choices(voucher)
        if not eligible_choices:
            return redirect("voucher:resubmit")
        else:
            return render(
                request,
                "enroll.html",
                context={
                    "eligible_choices": eligible_choices,
                    **get_base_context(self.request),
                },
            )

    def post(self, request):
        """
        Submit a CouponVersion object and redirect to the enrollment page
        """
        voucher = get_current_voucher(self.request.user)
        try:
            product_id, coupon_id = json.loads(request.POST["coupon_version"])
        except json.JSONDecodeError:
            messages.error(request, "Coupon Version is required.")
            return self.get(request)

        if product_id and coupon_id:
            # Ensure no one has snagged this coupon while the user was waiting
            if hasattr(Coupon.objects.get(id=coupon_id), "voucher"):
                new_coupon_version = get_valid_voucher_coupons_version(
                    voucher, Product.objects.get(id=product_id)
                )
                if new_coupon_version is None or not hasattr(
                    new_coupon_version, "coupon"
                ):
                    log.error(
                        "Found no valid coupons for matches for voucher %s", voucher.id
                    )
                    return redirect("voucher:resubmit")
                else:
                    coupon_id = new_coupon_version.coupon.id

            # Save coupon for this particular voucher
            voucher.coupon_id = coupon_id
            voucher.product_id = product_id
            voucher.save()
            enroll_url = make_checkout_url(
                product_id=product_id, code=voucher.coupon.coupon_code
            )
            return redirect(enroll_url)
        else:
            messages.error(request, "Coupon Version is required.")
            return self.get(request)


@login_required
def resubmit(request):
    """
    Prompt user to email voucher after failed voucher parsing
    """
    return render(request, "resubmit.html", context=get_base_context(request))


@login_required
def redeemed(request):
    """
    Coupon has already been redeemed
    """
    return render(request, "redeemed.html", context=get_base_context(request))
