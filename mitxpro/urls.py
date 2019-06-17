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
from oauth2_provider.urls import base_urlpatterns
from wagtail.admin import urls as wagtailadmin_urls
from wagtail.documents import urls as wagtaildocs_urls
from wagtail.core import urls as wagtail_urls

from mitxpro.views import index, restricted, AppContextView


urlpatterns = [
    path("admin/", admin.site.urls),
    path("status/", include("server_status.urls")),
    # NOTE: we only bring in base_urlpatterns so applications can only be created via django-admin
    path(
        "oauth2/",
        include((base_urlpatterns, "oauth2_provider"), namespace="oauth2_provider"),
    ),
    path("hijack/", include("hijack.urls")),
    path("", include("authentication.urls")),
    path("", include("courses.urls")),
    path("", include("courseware.urls")),
    path("", include("ecommerce.urls")),
    path("", include("users.urls")),
    path("", include("mail.urls")),
    path("voucher/", include(("voucher.urls", "voucher"))),
    path("api/app_context", AppContextView.as_view(), name="api-app_context"),
    # named routes mapped to the react app
    path("login/", index, name="login"),
    path("login/password/", index, name="login-password"),
    re_path(r"^login/forgot-password/$", index, name="password-reset"),
    re_path(
        r"^login/forgot-password/confirm/(?P<uid>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$",
        index,
        name="password-reset-confirm",
    ),
    path("signup/", index, name="signup"),
    path("signup/details/", index, name="signup-details"),
    path("signup/extra/", index, name="signup-extra"),
    path("signup/denied/", index, name="signup-denied"),
    path("signup/error/", index, name="signup-error"),
    path("signup/confirm/", index, name="register-confirm"),
    path("account/inactive/", index, name="account-inactive"),
    path("checkout/", index, name="checkout-page"),
    path("profile/", index, name="view-profile"),
    path("profile/edit/", index, name="edit-profile"),
    re_path(r"^ecommerce/admin/", restricted, name="ecommerce-admin"),
    # social django needs to be here to preempt the login
    path("", include("social_django.urls", namespace="social")),
    re_path(r"^dashboard/", index, name="user-dashboard"),
    # Wagtail
    re_path(r"^cms/", include(wagtailadmin_urls)),
    re_path(r"^documents/", include(wagtaildocs_urls)),
    path("", include(wagtail_urls)),
] + (
    static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
)

if settings.DEBUG:
    import debug_toolbar  # pylint: disable=wrong-import-position, wrong-import-order

    urlpatterns += [path("__debug__/", include(debug_toolbar.urls))]
