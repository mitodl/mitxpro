"""Ecommerce filters"""
from django_filters import rest_framework as filters

from courses.constants import VALID_PRODUCT_TYPE_CHOICES
from ecommerce.models import Product


class ProductFilter(filters.FilterSet):
    """Filters for Product model"""

    product_type = filters.ChoiceFilter(
        field_name="content_type__model", choices=VALID_PRODUCT_TYPE_CHOICES
    )

    class Meta:
        model = Product
        fields = []
