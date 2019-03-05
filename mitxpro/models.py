"""
Common model classes
"""
from django.db.models import DateTimeField, Manager, Model
from django.db.models.query import QuerySet

from mitxpro.utils import now_in_utc


class TimestampedModelQuerySet(QuerySet):
    """
    Subclassed QuerySet for TimestampedModelManager
    """

    def update(self, **kwargs):
        """
        Automatically update updated_on timestamp when .update(). This is because .update()
        does not go through .save(), thus will not auto_now, because it happens on the
        database level without loading objects into memory.
        """
        if "updated_on" not in kwargs:
            kwargs["updated_on"] = now_in_utc()
        return super().update(**kwargs)


class TimestampedModelManager(Manager):
    """
    Subclassed manager for TimestampedModel
    """

    def update(self, **kwargs):
        """
        Allows access to TimestampedModelQuerySet's update method on the manager
        """
        return self.get_queryset().update(**kwargs)

    def get_queryset(self):
        """
        Returns custom queryset
        """
        return TimestampedModelQuerySet(self.model, using=self._db)


class TimestampedModel(Model):
    """
    Base model for create/update timestamps
    """

    objects = TimestampedModelManager()
    created_on = DateTimeField(auto_now_add=True)  # UTC
    updated_on = DateTimeField(auto_now=True)  # UTC

    class Meta:
        abstract = True
