"""
Tests for render_bundle
"""
from django.test.client import RequestFactory
import pytest

from mitxpro.utils import webpack_dev_server_url
from mitxpro.templatetags.render_bundle import render_bundle


FAKE_COMMON_BUNDLE = [
    {
        "name": "common-1f11431a92820b453513.js",
        "path": "/project/static/bundles/common-1f11431a92820b453513.js",
    }
]


@pytest.fixture(autouse=True)
def dont_disable_webpack(settings):
    """Re-enable webpack loader stats for these tests."""
    settings.DISABLE_WEBPACK_LOADER_STATS = False


def test_debug(settings, mocker):
    """
    If USE_WEBPACK_DEV_SERVER=True, return a hot reload URL
    """
    settings.USE_WEBPACK_DEV_SERVER = True
    request = RequestFactory().get("/")
    context = {"request": request}

    # convert to generator
    common_bundle = (chunk for chunk in FAKE_COMMON_BUNDLE)
    get_bundle = mocker.Mock(return_value=common_bundle)
    loader = mocker.Mock(get_bundle=get_bundle)
    bundle_name = "bundle_name"

    get_loader = mocker.patch(
        "mitxpro.templatetags.render_bundle.get_loader", return_value=loader
    )
    assert render_bundle(context, bundle_name) == (
        '<script type="text/javascript" src="{base}/{filename}"  >'
        "</script>".format(
            base=webpack_dev_server_url(request), filename=FAKE_COMMON_BUNDLE[0]["name"]
        )
    )

    get_bundle.assert_called_with(bundle_name)
    get_loader.assert_called_with("DEFAULT")


def test_production(settings, mocker):
    """
    If USE_WEBPACK_DEV_SERVER=False, return a static URL for production
    """
    settings.USE_WEBPACK_DEV_SERVER = False
    request = RequestFactory().get("/")
    context = {"request": request}

    # convert to generator
    common_bundle = (chunk for chunk in FAKE_COMMON_BUNDLE)
    get_bundle = mocker.Mock(return_value=common_bundle)
    loader = mocker.Mock(get_bundle=get_bundle)
    bundle_name = "bundle_name"
    get_loader = mocker.patch(
        "mitxpro.templatetags.render_bundle.get_loader", return_value=loader
    )
    assert render_bundle(context, bundle_name) == (
        '<script type="text/javascript" src="{base}/{filename}"  >'
        "</script>".format(
            base="/static/bundles", filename=FAKE_COMMON_BUNDLE[0]["name"]
        )
    )

    get_bundle.assert_called_with(bundle_name)
    get_loader.assert_called_with("DEFAULT")


def test_missing_file(mocker):
    """
    If webpack-stats.json is missing, return an empty string
    """
    request = RequestFactory().get("/")
    context = {"request": request}

    get_bundle = mocker.Mock(side_effect=OSError)
    loader = mocker.Mock(get_bundle=get_bundle)
    bundle_name = "bundle_name"
    get_loader = mocker.patch(
        "mitxpro.templatetags.render_bundle.get_loader", return_value=loader
    )
    assert render_bundle(context, bundle_name) == ""

    get_bundle.assert_called_with(bundle_name)
    get_loader.assert_called_with("DEFAULT")
