"""
Common model classes
"""
from django.conf import settings
from django.contrib.postgres.fields import JSONField
from django.core.exceptions import ValidationError
from django.db.models import DateTimeField, ForeignKey, Manager, Model, PROTECT
from django.db.models.query import QuerySet
from django.db import transaction

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


class AuditModel(TimestampedModel):
    """An abstract base class for audit models"""

    acting_user = ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=PROTECT)
    data_before = JSONField(blank=True, null=True)
    data_after = JSONField(blank=True, null=True)

    class Meta:
        abstract = True

    @classmethod
    def get_related_field_name(cls):
        """
        Returns:
            str: A field name which links the Auditable model to this model
        """
        raise NotImplementedError


class AuditableModel(Model):
    """An abstract base class for auditable models"""

    class Meta:
        abstract = True

    def to_dict(self):
        """
        Returns:
            dict:
                A serialized representation of the model object
        """
        raise NotImplementedError

    @classmethod
    def objects_for_audit(cls):
        """
        Returns the correct model manager for the auditable model. This defaults to `objects`, but if
        a different manager is needed for any reason (for example, if `objects` is changed to a manager
        that applies some default filters), it can be overridden.

        Returns:
             django.db.models.manager.Manager: The correct model manager for the auditable model
        """
        return cls.objects

    @classmethod
    def get_audit_class(cls):
        """
        Returns:
            class of Model:
                A class of a Django model used as the audit table
        """
        raise NotImplementedError

    @transaction.atomic
    def save_and_log(self, acting_user, *args, **kwargs):
        """
        Saves the object and creates an audit object.

        Args:
            acting_user (User):
                The user who made the change to the model. May be None if inapplicable.
        """
        before_obj = self.objects_for_audit().filter(id=self.id).first()
        self.save(*args, **kwargs)
        self.refresh_from_db()
        before_dict = None
        if before_obj is not None:
            before_dict = before_obj.to_dict()

        audit_kwargs = dict(
            acting_user=acting_user, data_before=before_dict, data_after=self.to_dict()
        )
        audit_class = self.get_audit_class()
        audit_kwargs[audit_class.get_related_field_name()] = self
        audit_class.objects.create(**audit_kwargs)


class SingletonModel(Model):
    """Model class for models representing tables that should only have a single record"""

    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        if force_insert and self._meta.model.objects.count() > 0:
            raise ValidationError(
                "Only one {} object should exist. Update the existing object instead "
                "of creating a new one.".format(self.__class__.__name__)
            )
        return super().save(
            force_insert=force_insert,
            force_update=force_update,
            using=using,
            update_fields=update_fields,
        )

    class Meta:
        abstract = True
