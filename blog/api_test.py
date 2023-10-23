"""Tests for Blog API"""
import pytest

from blog.api import transform_blog_item


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
def test_transform_blog_item(category, expected_category):
    item = {
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
        "category": category,
        "pubDate": "Fri, 06 Oct 2023 13:30:00 GMT",
        "author": "mitxpro@mit.edu (MIT xPRO)",
        "guid": "https://curve.mit.edu/ask-an-mit-professor-the-science-behind-oppenheimer",
        "dc:date": "2023-10-06T13:30:00Z",
    }

    transform_blog_item(item)
    assert all(
        key not in item
        for key in ["pubDate", "dc:date", "content:encoded", "author", "guid"]
    )
    assert all(
        key in item
        for key in [
            "title",
            "link",
            "description",
            "category",
            "banner_image",
            "published_date",
        ]
    )

    assert item["title"] == "Ask an MIT Professor: The Science Behind Oppenheimer"
    assert (
        item["link"]
        == "https://curve.mit.edu/ask-an-mit-professor-the-science-behind-oppenheimer"
    )
    assert (
        item["description"]
        == "It’s not every day you see a topic like quantum physics represented in a hit "
        "summer movie. Yet Christopher Nolan’s Oppenheimer has dazzled audiences everywhere"
        " and is on track to earn nearly $1 billion at the global box office."
    )
    assert item["category"] == expected_category
    assert (
        item["banner_image"]
        == "https://curve.mit.edu/hubfs/Screenshot%202023-10-05%20at%203.55.25%20PM.png"
    )
    assert item["published_date"] == "October 6th, 2023"
