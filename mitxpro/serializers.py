"""MIT xPro serializers"""

from django.conf import settings
from rest_framework import serializers

from mitxpro.utils import public_path


class AppContextSerializer(serializers.Serializer):
    """Serializer for the application context"""

    public_path = serializers.SerializerMethodField()
    gtm_tracking_id = serializers.SerializerMethodField()
    ga_tracking_id = serializers.SerializerMethodField()
    environment = serializers.SerializerMethodField()
    release_version = serializers.SerializerMethodField()
    features = serializers.SerializerMethodField()

    def get_features(self, request):  # noqa: ARG002
        """Returns a dictionary of features"""
        return {}

    def get_release_version(self, request):  # noqa: ARG002
        """Returns a dictionary of features"""
        return settings.VERSION

    def get_gtm_tracking_id(self, request):  # noqa: ARG002
        """Returns the GTM container ID"""
        return settings.GTM_TRACKING_ID

    def get_ga_tracking_id(self, request):  # noqa: ARG002
        """Returns a dictionary of features"""
        return settings.GA_TRACKING_ID

    def get_environment(self, request):  # noqa: ARG002
        """Returns a dictionary of features"""
        return settings.ENVIRONMENT

    def get_public_path(self, request):
        """Returns the public_path"""
        return public_path(request)


class WriteableSerializerMethodField(serializers.SerializerMethodField):
    """
    A SerializerMethodField which has been marked as not read_only so that submitted data passed validation.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.read_only = False

    def to_internal_value(self, data):
        return data
