from datetime import datetime

from bs4 import BeautifulSoup
from django.utils.dateparse import parse_datetime
from django.utils.dateformat import DateFormat


def transform_blog_item(item):
    description = item["description"]
    soup = BeautifulSoup(description, "html.parser")
    item["description"] = soup.text

    image_tags = soup.find_all("img")
    item["banner_image"] = image_tags[0].get("src")

    published_date = parse_datetime(item["dc:date"])
    df = DateFormat(published_date)
    item["published_date"] = df.format("F jS, Y")
