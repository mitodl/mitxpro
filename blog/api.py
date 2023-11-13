"""API for the Blog app"""
from datetime import datetime

from bs4 import BeautifulSoup
from django.utils.dateformat import DateFormat
from django.utils.dateparse import parse_datetime


def transform_blog_item(item):
    description = item["description"]
    soup = BeautifulSoup(description, "html.parser")
    item["description"] = soup.text.strip()

    image_tags = soup.find_all("img")
    item["banner_image"] = image_tags[0].get("src")

    published_date = parse_datetime(item["dc:date"])
    df = DateFormat(published_date)
    item["published_date"] = df.format("F jS, Y")

    item["categories"] = (
        item["category"] if type(item["category"]) == list else [item["category"]]
    )

    del item["content:encoded"]
    del item["pubDate"]
    del item["dc:date"]
    del item["author"]
    del item["guid"]
