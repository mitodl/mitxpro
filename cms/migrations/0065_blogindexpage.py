# Generated by Django 3.2.23 on 2023-11-16 16:26

import datetime
import json

import django.db.models.deletion
import pytz
import wagtailmetadata.models
from django.db import migrations, models
from wagtail.models import Page, PageRevision

import cms.models


def create_blog_index_page(apps, app_schema):
    """
    Creates index page for blog
    """
    Site = apps.get_model("wagtailcore", "Site")
    site = Site.objects.filter(is_default_site=True).first()
    if not site:
        raise Exception(
            "A default site is not set up. Please setup a default site before running this migration"
        )
    if not site.root_page:
        raise Exception(
            "No root (home) page set up. Please setup a root (home) page for the default site before running this migration"
        )

    home_page = Page.objects.get(id=site.root_page.id)
    BlogIndexPage = apps.get_model("cms", "BlogIndexPage")
    ContentType = apps.get_model("contenttypes", "ContentType")

    blog_index_content_type, _ = ContentType.objects.get_or_create(
        app_label="cms", model="blogindexpage"
    )
    blog_index = BlogIndexPage.objects.first()

    if not blog_index:
        blog_page_content = dict(
            title="Blog",
            content_type_id=blog_index_content_type.id,
            locale_id=home_page.get_default_locale().id,
        )
        blog_page_obj = BlogIndexPage(**blog_page_content)
        home_page.add_child(instance=blog_page_obj)
        # NOTE: This block of code creates page revision and publishes it. There may be an easier way to do this.
        content = dict(**blog_page_content, pk=blog_page_obj.id)
        revision = PageRevision.objects.create(
            page_id=blog_page_obj.id,
            submitted_for_moderation=False,
            created_at=datetime.datetime.now(tz=pytz.UTC),
            content=content,
        )
        revision.publish()


class Migration(migrations.Migration):

    dependencies = [
        ("wagtailimages", "0023_add_choose_permissions"),
        ("wagtailcore", "0062_comment_models_and_pagesubscription"),
        ("wagtailredirects", "0008_add_verbose_name_plural"),
        ("cms", "0064_productpage_format_field"),
    ]

    operations = [
        migrations.CreateModel(
            name="BlogIndexPage",
            fields=[
                (
                    "page_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="wagtailcore.page",
                    ),
                ),
                (
                    "sub_heading",
                    models.CharField(
                        blank=True,
                        default="Online learning stories for professionals, from MIT",
                        help_text="Sub heading of the blog page.",
                        max_length=250,
                        null=True,
                    ),
                ),
                (
                    "recent_posts_heading",
                    models.CharField(
                        blank=True,
                        default="Top Most Recent Posts",
                        help_text="Heading of the recent posts section.",
                        max_length=250,
                        null=True,
                    ),
                ),
                (
                    "more_posts_heading",
                    models.CharField(
                        blank=True,
                        default="More From MIT",
                        help_text="Heading of the more posts section.",
                        max_length=250,
                        null=True,
                    ),
                ),
                (
                    "banner_image",
                    models.ForeignKey(
                        blank=True,
                        help_text="Banner image for the Blog page.",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to="wagtailimages.image",
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
            bases=("wagtailcore.page",),
        ),
        migrations.RunPython(create_blog_index_page, migrations.RunPython.noop),
    ]
