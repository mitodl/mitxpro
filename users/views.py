"""User views"""
from oauth2_provider.contrib.rest_framework import IsAuthenticatedOrTokenHasScope
from rest_framework import mixins, viewsets

from mitxpro.permissions import UserIsOwnerPermission
from users.models import User
from users.serializers import UserSerializer


class UserRetrieveViewSet(mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """User retrieve viewsets"""

    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticatedOrTokenHasScope, UserIsOwnerPermission]
    required_scopes = ["user"]

    def get_object(self):
        # allow a special case /api/users/me so the end application can request
        # this without needing the current user's id
        if self.kwargs["pk"] == "me":
            return self.request.user

        return super().get_object()
