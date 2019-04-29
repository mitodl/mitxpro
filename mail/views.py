"""Mail views"""
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from mail import api
from mail.constants import EMAIL_VERIFICATION, EMAIL_PW_RESET, EMAIL_BULK_ENROLL
from mail.forms import EmailDebuggerForm


EMAIL_DEBUG_EXTRA_CONTEXT = {
    EMAIL_PW_RESET: {"uid": "abc-def", "token": "abc-def"},
    EMAIL_VERIFICATION: {"confirmation_url": "http://www.example.com/confirm/url"},
    EMAIL_BULK_ENROLL: {
        "enrollable_title": "Dummy Course Title",
        "enrollment_url": "http://www.example.com/enroll?course_id=1234",
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
