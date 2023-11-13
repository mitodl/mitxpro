"""blog app settings"""
from django.apps import AppConfig


class BlogConfig(AppConfig):
    """AppConfig for blog"""
    default_auto_field = "django.db.models.BigAutoField"
    name = "blog"
