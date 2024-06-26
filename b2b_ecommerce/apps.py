"""b2b_ecommerce app settings"""

from django.apps import AppConfig


class B2BEcommerceConfig(AppConfig):
    """AppConfig for B2B_Ecommerce"""

    name = "b2b_ecommerce"

    def ready(self):
        """Application is ready"""
        import b2b_ecommerce.signals  # noqa: F401
