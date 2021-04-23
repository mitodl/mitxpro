"""Custom strategy"""
from social_django.strategy import DjangoStrategy


class DjangoRestFrameworkStrategy(DjangoStrategy):
    """Strategy specific to handling DRF requests"""

    def __init__(self, storage, drf_request=None, tpl=None):
        self.drf_request = drf_request
        # pass the original django request to DjangoStrategy
        request = drf_request._request  # pylint: disable=protected-access
        super().__init__(storage, request=request, tpl=tpl)

    def request_data(self, merge=True):
        """Returns the request data"""
        if not self.drf_request:
            return {}

        # DRF stores json payload data here, not in request.POST or request.GET like PSA expects
        return self.drf_request.data
