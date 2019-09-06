"""Mail views"""
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from mail import api
from mail.constants import (
    EMAIL_VERIFICATION,
    EMAIL_PW_RESET,
    EMAIL_BULK_ENROLL,
    EMAIL_B2B_RECEIPT,
)
from mail.forms import EmailDebuggerForm


EMAIL_DEBUG_EXTRA_CONTEXT = {
    EMAIL_PW_RESET: {"uid": "abc-def", "token": "abc-def"},
    EMAIL_VERIFICATION: {"confirmation_url": "http://www.example.com/confirm/url"},
    EMAIL_BULK_ENROLL: {
        "enrollable_title": "Dummy Course Title",
        "enrollment_url": "http://www.example.com/enroll?course_id=1234",
    },
    EMAIL_B2B_RECEIPT: {
        "download_url": "http://b2b.example.com",
        "title": "Course run or Program title",
        "run_date_range": "Jan 1, 2020 - Mar 15, 2020",
        "item_price": "$12,345.12",
        "total_price": "$14,690.24",
        "discount": "$10,000.00",
        "num_seats": "2",
        "order_reference_id": "XPRO-ENROLLMENT-user.mitxpro-3",
        "readable_id": "program-v1:xPRO+AMx",
        "email": "mitx-purchaser@example.com",
        "purchase_date": "May 30, 2019",
    },
}


@method_decorator(csrf_exempt, name="dispatch")
class EmailDebuggerView(View):
    """Email debugger view"""

    form_cls = EmailDebuggerForm
    initial = {}
    template_name = "email_debugger.html"

    def get(self, request):
        """
        Dispalys the debugger UI
        """
        form = self.form_cls(initial=self.initial)
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        """
        Renders a test email
        """
        form = self.form_cls(request.POST)

        if not form.is_valid():
            return JsonResponse({"error": "invalid input"})

        email_type = form.cleaned_data["email_type"]
        context = {"base_url": settings.SITE_BASE_URL, "site_name": settings.SITE_NAME}

        email_extra_context = EMAIL_DEBUG_EXTRA_CONTEXT.get(email_type, {})
        context.update(email_extra_context)

        subject, text_body, html_body = api.render_email_templates(email_type, context)

        return JsonResponse(
            {"subject": subject, "html_body": html_body, "text_body": text_body}
        )
