"""Views for courseware"""
from django.http import HttpResponse
from rest_framework import status


def openedx_private_auth_complete(request):
    """Responds with a simple HTTP_200_OK"""
    # NOTE: this is only meant as a landing endpoint for api.create_edx_auth_token() flow
    return HttpResponse(status=status.HTTP_200_OK)
