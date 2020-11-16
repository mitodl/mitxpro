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

from django.conf import settings
from django.conf.urls import include
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, re_path
from django.views.decorators.cache import cache_control
from oauth2_provider.urls import base_urlpatterns
from wagtail.admin import urls as wagtailadmin_urls
from wagtail.documents import urls as wagtaildocs_urls
from wagtail.core import urls as wagtail_urls
from wagtail.images.views.serve import ServeView
from wagtail.utils.urlpatterns import decorate_urlpatterns

from mitxpro.views import (
    index,
    restricted,
    AppContextView,
    handler404 as not_found_handler,
    handler500 as server_error_handler,
    cms_signin_redirect_to_site_signin,
)

WAGTAIL_IMG_CACHE_AGE = 31_536_000  # 1 year


urlpatterns = (
    [
        path("admin/", admin.site.urls),
        path("status/", include("server_status.urls")),
        # NOTE: we only bring in base_urlpatterns so applications can only be created via django-admin
        path(
            "oauth2/",
            include((base_urlpatterns, "oauth2_provider"), namespace="oauth2_provider"),
        ),
        path("hijack/", include("hijack.urls")),
        path("", include("authentication.urls")),
        path("", include("b2b_ecommerce.urls")),
        path("", include("courses.urls")),
        path("", include("courseware.urls")),
        path("", include("ecommerce.urls")),
        path("", include("users.urls")),
        path("", include("sheets.urls")),
        path("", include("mail.urls")),
        path("api/v1/", include("mitol.digitalcredentials.urls")),
        path("", include("mitol.mail.urls")),
        path("boeing/", include(("voucher.urls", "voucher"))),
        path("api/app_context", AppContextView.as_view(), name="api-app_context"),
        # named routes mapped to the react app
        path("signin/", index, name="login"),
        path("signin/password/", index, name="login-password"),
        re_path(r"^signin/forgot-password/$", index, name="password-reset"),
        re_path(
            r"^signin/forgot-password/confirm/(?P<uid>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$",
            index,
            name="password-reset-confirm",
        ),
        path("create-account/", index, name="signup"),
        path("create-account/details/", index, name="signup-details"),
        path("create-account/extra/", index, name="signup-extra"),
        path("create-account/denied/", index, name="signup-denied"),
        path("create-account/error/", index, name="signup-error"),
        path("create-account/confirm/", index, name="register-confirm"),
        path("account/inactive/", index, name="account-inactive"),
        path("account/confirm-email/", index, name="account-confirm-email-change"),
        path("checkout/", index, name="checkout-page"),
        path("profile/", index, name="view-profile"),
        path("profile/edit/", index, name="edit-profile"),
        re_path(r"^ecommerce/admin/", restricted, name="ecommerce-admin"),
        # social django needs to be here to preempt the login
        path("", include("social_django.urls", namespace="social")),
        re_path(r"^dashboard/", index, name="user-dashboard"),
        re_path(r"^receipt/(?P<pk>\d+)/", index, name="order-receipt"),
        re_path(r"^account-settings/", index, name="account-settings"),
        # Wagtail
        re_path(
            r"^cms/login", cms_signin_redirect_to_site_signin, name="wagtailadmin_login"
        ),
        re_path(r"^cms/", include(wagtailadmin_urls)),
        re_path(r"^documents/", include(wagtaildocs_urls)),
    ]
    + decorate_urlpatterns(
        # NOTE: This route enables dynamic Wagtail image loading. It comes directly from the Wagtail docs:
        #       https://docs.wagtail.io/en/v2.7/advanced_topics/images/image_serve_view.html#setup
        [
            re_path(
                r"^images/([^/]*)/(\d*)/([^/]*)/[^/]*$",
                ServeView.as_view(),
                name="wagtailimages_serve",
            )
        ],
        cache_control(max_age=WAGTAIL_IMG_CACHE_AGE),
    )
    + [
        path("", include(wagtail_urls)),
        # Add custom URL patterns that will also serve Wagtail pages
        path("", include("cms.urls")),
        path("robots.txt", include("robots.urls")),
    ]
    + (
        static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
        + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    )
)

handler404 = not_found_handler
handler500 = server_error_handler

if settings.DEBUG:
    import debug_toolbar  # pylint: disable=wrong-import-position, wrong-import-order

    urlpatterns += [path("__debug__/", include(debug_toolbar.urls))]
