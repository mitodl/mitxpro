from rest_framework.filters import BaseFilterBackend


class ReadableIDFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        field_name = "readable_id"
        if field_name in request.GET:
            value = request.GET[field_name].replace(" ", "+")
            queryset = queryset.filter(**{field_name: value})
        return queryset
