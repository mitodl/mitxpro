"""Mail forms"""
from django import forms


class EmailDebuggerForm(forms.Form):
    """Form for email debugger"""

    email_type = forms.ChoiceField(
        choices=(("verification", "Verify Email"), ("password_reset", "Password Reset"))
    )
