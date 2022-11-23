"""project URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import re_path
from django.views.decorators.cache import cache_control
from mitol.common.decorators import cache_control_max_age_jitter
from wagtail.images.views.serve import ServeView
from wagtail.utils.urlpatterns import decorate_urlpatterns

from mitxpro.views import (
    handler404 as not_found_handler,
    handler500 as server_error_handler,
)

WAGTAIL_IMG_CACHE_AGE = 31_536_000  # 1 year


urlpatterns = (
    decorate_urlpatterns(
        # NOTE: This route enables dynamic Wagtail image loading. It comes directly from the Wagtail docs:
        #       https://docs.wagtail.io/en/v2.7/advanced_topics/images/image_serve_view.html#setup
        [
            re_path(
                r"^images/([^/]*)/(\d*)/([^/]*)/[^/]*$",
                ServeView.as_view(),
                name="wagtailimages_serve",
            )
        ],
        cache_control_max_age_jitter(cache_control, max_age=WAGTAIL_IMG_CACHE_AGE),
    )
)

handler404 = not_found_handler
handler500 = server_error_handler