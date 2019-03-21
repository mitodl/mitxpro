"""Custom strategy"""
from rest_framework.request import Request
from social_django.strategy import DjangoStrategy


class DjangoRestFrameworkStrategy(DjangoStrategy):
    """Strategy specific to handling DRF requests"""

    def __init__(self, storage, drf_request=None, tpl=None):
        self.drf_request = drf_request
        # pass the original django request to DjangoStrategy
        request = drf_request._request  # pylint: disable=protected-access
        super().__init__(storage, request=request, tpl=tpl)

    def clean_authenticate_args(self, *args, **kwargs):
        """Cleanup request argument if present, which is passed to authenticate as for Django 1.11"""
        # this is similar to what DjangoStrategy does, but is specific to DRF's Request type
        if len(args) > 0 and isinstance(args[0], Request):
            kwargs["request"], args = args[0], args[1:]

        return super().clean_authenticate_args(*args, **kwargs)

    def request_data(self, merge=True):
        """Returns the request data"""
        if not self.drf_request:
            return {}

        # DRF stores json payload data here, not in request.POST or request.GET like PSA expects
        return self.drf_request.data
