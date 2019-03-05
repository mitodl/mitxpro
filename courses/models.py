"""
Course models
"""
import logging
from django.db import models

from mitxpro.models import TimestampedModel

log = logging.getLogger(__name__)


class Program(TimestampedModel):
    """Model for a program of courses"""

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    thumbnail = models.ImageField(null=True, blank=True)
    readable_id = models.CharField(null=True, max_length=255)
    live = models.BooleanField(default=False)

    def __str__(self):
        return self.title


class Course(TimestampedModel):
    """Model for a course"""

    program = models.ForeignKey(Program, on_delete=models.CASCADE, null=True)
    position_in_program = models.PositiveSmallIntegerField(null=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    thumbnail = models.ImageField(null=True, blank=True)
    readable_id = models.CharField(null=True, max_length=255)
    live = models.BooleanField(default=False)

    class Meta:
        ordering = ("program", "title")

    def __str__(self):
        return self.title


class CourseRun(TimestampedModel):
    """Model for a single run/instance of a course"""

    course = models.ForeignKey(Course, null=True, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    courseware_id = models.CharField(max_length=255, blank=True, null=True, unique=True)
    courseware_url = models.URLField(null=True)
    start_date = models.DateTimeField(null=True, db_index=True)
    end_date = models.DateTimeField(null=True, db_index=True)
    enrollment_start = models.DateTimeField(null=True, db_index=True)
    enrollment_end = models.DateTimeField(null=True, db_index=True)
    live = models.BooleanField(default=False)

    def __str__(self):
        return self.title
