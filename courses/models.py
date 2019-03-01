"""
Models for course structure
"""
import logging

from django.db import models


log = logging.getLogger(__name__)


VALID_PLATFORMS = ("edx.org", "Open edX")
VALID_PLATFORM_CHOICES = list(
    zip(VALID_PLATFORMS, VALID_PLATFORMS)
)


class Program(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    thumbnail = models.ImageField(null=True, blank=True)
    readable_id = models.CharField(null=True, max_length=255)
    live = models.BooleanField(default=False)
    source = models.CharField(
        max_length=15,
        choices=VALID_PLATFORM_CHOICES,
        null=True
    )

    def __str__(self):
        return self.title


class Course(models.Model):
    program = models.ForeignKey(Program, on_delete=models.CASCADE, null=True)
    position_in_program = models.PositiveSmallIntegerField(null=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    thumbnail = models.ImageField(null=True, blank=True)
    readable_id = models.CharField(null=True, max_length=255)
    live = models.BooleanField(default=False)
    source = models.CharField(
        max_length=15,
        choices=VALID_PLATFORM_CHOICES,
        null=True
    )

    class Meta:
        ordering = ('program', 'title', )

    def __str__(self):
        return self.title


class CourseRun(models.Model):
    course = models.ForeignKey(Course, null=True, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    courseware_id = models.CharField(max_length=255, blank=True, null=True, unique=True)
    courseware_url = models.URLField(null=True)
    start_date = models.DateTimeField(null=True, db_index=True)
    end_date = models.DateTimeField(null=True, db_index=True)
    enrollment_start = models.DateTimeField(null=True, db_index=True)
    enrollment_end = models.DateTimeField(null=True, db_index=True)
    live = models.BooleanField(default=False)
    platform = models.CharField(
        max_length=15,
        choices=VALID_PLATFORM_CHOICES,
        null=True
    )

    def __str__(self):
        return self.title
