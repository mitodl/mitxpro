"""JS interop template tag tests"""

from django.template import Context, Template


def test_js_settings(mocker, rf):
    """Test the template tag js_settings"""
    mocker.patch(
        "mitxpro.templatetags.js_interop.get_js_settings",
        return_value={"data": "value"},
    )

    request = rf.get("/")
    context = Context({"request": request})
    template = Template("{% load js_interop %}{% js_settings %}")

    rendered_template = template.render(context)
    assert (
        rendered_template
        == """<script type="text/javascript">
var SETTINGS = {"data": "value"};
</script>"""
    )
