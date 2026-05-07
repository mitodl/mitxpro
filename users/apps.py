"""Users application"""

from django.apps import AppConfig
from wagtail.users.apps import WagtailUsersAppConfig


class UsersConfig(AppConfig):
    """Config for users app"""

    name = "users"


class MitxproWagtailUsersAppConfig(WagtailUsersAppConfig):
    """
    Custom WagtailUsersAppConfig for the mitxpro User model.

    The viewset string is resolved lazily by Wagtail after the app registry is
    ready, so no Django model imports are needed here.
    """

    user_viewset = "users.wagtail_views.UserViewSet"
