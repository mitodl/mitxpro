"""Mail forms"""

from django import forms

from mail.constants import EMAIL_TYPE_DESCRIPTIONS


class EmailDebuggerForm(forms.Form):
    """Form for email debugger"""

    email_type = forms.ChoiceField(choices=(EMAIL_TYPE_DESCRIPTIONS.items()))
