"""Mail views"""
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from mail import api
from mail.forms import EmailDebuggerForm


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
        context = {"base_url": settings.SITE_BASE_URL, "anon_token": "abc123"}

        # static, dummy data
        if email_type == "password_reset":
            context.update({"uid": "abc-def", "token": "abc-def"})
        elif email_type == "verification":
            context.update({"confirmation_url": "http://www.example.com/comfirm/url"})

        subject, text_body, html_body = api.render_email_templates(email_type, context)

        return JsonResponse(
            {"subject": subject, "html_body": html_body, "text_body": text_body}
        )
