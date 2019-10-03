from django.db import models


class GoogleToken(models.Model):
    value = models.BinaryField()
