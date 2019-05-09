import json
import pytest

from cms.factories import ResourcePageFactory, ResourceBlockFactory

pytestmark = [pytest.mark.django_db]


def test_resource_page():
    """
    Verify user can create resource page.
    """
    page = ResourcePageFactory.create(
        title="title of the page",
        sub_heading="sub heading of the page",
        content=json.dumps(
            [
                {
                    "type": "content",
                    "value": {
                        "heading": "Introduction",
                        "detail": "details of introduction",
                    },
                }
            ]
        ),
    )

    assert page.title == "title of the page"
    assert page.sub_heading == "sub heading of the page"

    for block in page.content:  # pylint: disable=not-an-iterable
        assert block.block_type == "content"
        assert block.value["heading"] == "Introduction"
        assert block.value["detail"].source == "details of introduction"


def test_resource_page_unique_slug():
    """
    Verify that if user creates pages with same title, there slug would be auto generated uniquely.
    """
    page = ResourcePageFactory(title="title of the page")
    another_page = ResourcePageFactory(title="title of the page")
    assert not page.slug == another_page.slug
