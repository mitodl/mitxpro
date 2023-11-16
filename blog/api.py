"""API for the Blog app"""
import logging

import requests
import xmltodict
from bs4 import BeautifulSoup
from django.utils.dateformat import DateFormat
from django.utils.dateparse import parse_datetime


log = logging.getLogger()

RSS_FEED_URL = "https://curve.mit.edu/rss.xml"


def parse_blog(item: dict):
    """
    Parses a blog item

    Args:
        item (dict): Dict of blog post data
    """
    if not isinstance(item, dict):
        log.error(
            "Could not parse blog post. Expecting a dict type but got: ", type(item)
        )

    if not all(key in item for key in ["description", "dc:date", "category"]):
        log.error("Could not parse blog post. Expected data is missing", item)

    description = item["description"]
    soup = BeautifulSoup(description, "html.parser")
    item["description"] = soup.text.strip()

    image_tags = soup.find_all("img")
    item["banner_image"] = image_tags[0].get("src")

    published_date = parse_datetime(item["dc:date"])
    published_date_format = DateFormat(published_date)
    item["published_date"] = published_date_format.format("F jS, Y")

    item["categories"] = (
        item["category"] if isinstance(item["category"], list) else [item["category"]]
    )

    item.pop("content:encoded", None)
    item.pop("pubDate", None)
    item.pop("dc:date", None)
    item.pop("author", None)
    item.pop("guid", None)
    item.pop("category", None)


def fetch_blog():
    """
    Fetch and parse RSS feed
    """
    resp = requests.get(RSS_FEED_URL, timeout=60)
    resp.raise_for_status()
    resp_dict = xmltodict.parse(resp.content)

    items = resp_dict.get("rss", {}).get("channel", {}).get("item", [])
    for item in items:
        parse_blog(item)

    return items
