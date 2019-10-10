"""HTTP views for sheets app"""
import logging

from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from rest_framework import status

import gspread

log = logging.getLogger(__name__)


@csrf_exempt
def handle_file_push_notification(request):
    log.critical("********* GOT THE PUSH NOTIFICATION!!! *********")
    log.critical(str(request.headers))
    log.critical("body...")
    log.critical(str(request.body))
    return HttpResponse(status=status.HTTP_200_OK)
