"""Wagtail hooks for courses app"""

from wagtail import hooks

from ecommerce.wagtail_views import ProductViewSetGroup


@hooks.register("register_admin_viewset")
def register_viewset():
    """
    Wagtail hook to register the ProductViewSetGroup.
    """
    return ProductViewSetGroup()
