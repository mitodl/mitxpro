"""JS interopability template tags"""
import json

from django import template
from django.utils.safestring import mark_safe

from mitxpro.utils import get_js_settings

register = template.Library()


@register.simple_tag(takes_context=True)
def js_settings(context):
    """Renders the JS settings object to a script tag"""
    request = context["request"]
    js_settings_json = json.dumps(get_js_settings(request))

    return mark_safe(
        f"""<script type="text/javascript">
var SETTINGS = {js_settings_json};
</script>"""
    )
