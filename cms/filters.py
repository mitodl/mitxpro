"""
Custom filter backends for Wagtail API.
"""

from rest_framework.filters import BaseFilterBackend


class ReadableIDFilter(BaseFilterBackend):
    """
    Filter backend to filter queryset by readable_id.
    """

    def filter_queryset(self, request, queryset, view):
        """
        Filters the queryset based on the readable_id parameter in the request.
        """
        field_name = "readable_id"
        if field_name in request.GET:
            value = request.GET[field_name].replace(" ", "+")
            queryset = queryset.filter(**{field_name: value})
        return queryset
