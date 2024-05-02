"""ecommerce app settings"""

from django.apps import AppConfig


class EcommerceConfig(AppConfig):
    """AppConfig for Ecommerce"""

    name = "ecommerce"

    def ready(self):
        """Application is ready"""
        import ecommerce.signals  # noqa: F401
