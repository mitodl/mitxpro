"""Tests for Blog API"""
import pytest

from blog.api import fetch_blog, parse_blog


@pytest.fixture
def valid_blog_post():
    """Fixture that returns a valid blog post"""
    return {
        "title": "Ask an MIT Professor: The Science Behind Oppenheimer",
        "link": "https://curve.mit.edu/ask-an-mit-professor-the-science-behind-oppenheimer",
        "description": '<div class="hs-featured-image-wrapper"> \n <a '
        'href="https://curve.mit.edu/ask-an-mit-professor-the-science-behind-oppenheimer" title="" '
        'class="hs-featured-image-link"> <img '
        'src="https://curve.mit.edu/hubfs/Screenshot%202023-10-05%20at%203.55.25%20PM.png" alt="Ask '
        'an MIT Professor: The Science Behind Oppenheimer" class="hs-featured-image" '
        'style="width:auto !important; max-width:50%; float:left; margin:0 15px 15px 0;"> </a> '
        "\n</div> \n<p>It’s not every day you see a topic like quantum physics represented in a hit "
        'summer movie. Yet Christopher Nolan’s <span style="font-style: italic;">Oppenheimer</span> '
        "has dazzled audiences everywhere and is on track to earn nearly <a "
        'href="https://www.forbes.com/sites/markhughes/2023/09/23/can-oppenheimer-top-1-billion-box'
        '-office-the-clock-is-ticking/?sh=164424195cfe">$1 billion at the global box '
        "office</a>.&nbsp;</p>",
        "content:encoded": '<div class="hs-featured-image-wrapper"> \n <a '
        'href="https://curve.mit.edu/ask-an-mit-professor-the-science-behind-oppenheimer" title="" '
        'class="hs-featured-image-link"> <img '
        'src="https://curve.mit.edu/hubfs/Screenshot%202023-10-05%20at%203.55.25%20PM.png" alt="Ask '
        'an MIT Professor: The Science Behind Oppenheimer" class="hs-featured-image" '
        'style="width:auto !important; max-width:50%; float:left; margin:0 15px 15px 0;"> </a> '
        "\n</div> \n<p>It’s not every day you see a topic like quantum physics represented in a hit "
        'summer movie. Yet Christopher Nolan’s <span style="font-style: italic;">Oppenheimer</span> '
        "has dazzled audiences everywhere and is on track to earn nearly <a "
        'href="https://www.forbes.com/sites/markhughes/2023/09/23/can-oppenheimer-top-1-billion-box'
        '-office-the-clock-is-ticking/?sh=164424195cfe">$1 billion at the global box '
        "office</a>.&nbsp;</p>",
        "category": "Online Learning",
        "pubDate": "Fri, 06 Oct 2023 13:30:00 GMT",
        "author": "mitxpro@mit.edu (MIT xPRO)",
        "guid": "https://curve.mit.edu/ask-an-mit-professor-the-science-behind-oppenheimer",
        "dc:date": "2023-10-06T13:30:00Z",
    }


@pytest.mark.parametrize(
    "category, expected_category",
    [
        ["Quantum Computing", ["Quantum Computing"]],
        [
            ["Quantum Computing", "Online Education"],
            ["Quantum Computing", "Online Education"],
        ],
    ],
)
def test_parse_blog(
    category, expected_category, valid_blog_post
):  # pylint: disable=redefined-outer-name
    """
    Tests that `parse_blog` parses a blog post as required.
    """
    valid_blog_post["category"] = category
    parse_blog(valid_blog_post)
    assert all(
        key not in valid_blog_post
        for key in [
            "pubDate",
            "dc:date",
            "content:encoded",
            "author",
            "guid",
            "category",
        ]
    )
    assert all(
        key in valid_blog_post
        for key in [
            "title",
            "link",
            "description",
            "categories",
            "banner_image",
            "published_date",
        ]
    )

    assert (
        valid_blog_post["title"]
        == "Ask an MIT Professor: The Science Behind Oppenheimer"
    )
    assert (
        valid_blog_post["link"]
        == "https://curve.mit.edu/ask-an-mit-professor-the-science-behind-oppenheimer"
    )
    assert (
        valid_blog_post["description"]
        == "It’s not every day you see a topic like quantum physics represented in a hit "
        "summer movie. Yet Christopher Nolan’s Oppenheimer has dazzled audiences everywhere"
        " and is on track to earn nearly $1 billion at the global box office."
    )
    assert valid_blog_post["categories"] == expected_category
    assert (
        valid_blog_post["banner_image"]
        == "https://curve.mit.edu/hubfs/Screenshot%202023-10-05%20at%203.55.25%20PM.png"
    )
    assert valid_blog_post["published_date"] == "October 6th, 2023"


def test_fetch_blog():
    """Test that `fetch_blog` fetches the RSS feed and returns transformed blog"""
    items = fetch_blog()
    assert isinstance(items, list)
    assert len(items) > 0
    first_blog = items[0]
    assert all(
        key in first_blog
        for key in [
            "title",
            "link",
            "description",
            "categories",
            "banner_image",
            "published_date",
        ]
    )


def test_parse_blog_invalid_type_and_data(
    mocker, valid_blog_post
):  # pylint: disable=redefined-outer-name
    """
    Test that `parse_blog` logs error when post item type or data is not valid.
    """
    mock_log = mocker.patch("blog.api.log")

    random_object = object()
    parse_blog(random_object)
    mock_log.error.assert_called_with(
        "Could not parse blog post. Expecting a dict type but got: %s",
        type(random_object),
    )

    valid_blog_post.pop("description", None)
    valid_blog_post.pop("dc:date", None)
    valid_blog_post.pop("category", None)
    parse_blog(valid_blog_post)
    mock_log.error.assert_called_with(
        "Could not parse blog post. Expected data is missing. Post Data: %s",
        valid_blog_post,
    )
