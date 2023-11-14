"""API for the Blog app"""
import requests
import xmltodict
from bs4 import BeautifulSoup
from django.utils.dateformat import DateFormat
from django.utils.dateparse import parse_datetime


def transform_blog_item(item):
    """
    Transforms a blog item
    """
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

    del item["content:encoded"]
    del item["pubDate"]
    del item["dc:date"]
    del item["author"]
    del item["guid"]
    del item["category"]


def fetch_blogs():
    """
    Fetch and parse RSS feed
    """
    rss_feed_url = "https://curve.mit.edu/rss.xml"
    resp = requests.get(rss_feed_url, timeout=60)
    resp.raise_for_status()
    resp_dict = xmltodict.parse(resp.content)

    items = resp_dict.get("rss", {}).get("channel", {}).get("item", [])
    for item in items:
        transform_blog_item(item)

    return items
