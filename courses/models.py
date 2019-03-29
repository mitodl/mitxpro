"""
Course models
"""
import logging
from django.db import models

from mitxpro.models import TimestampedModel
from courseware.utils import edx_redirect_url

log = logging.getLogger(__name__)


class Program(TimestampedModel):
    """Model for a course program"""

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    thumbnail = models.ImageField(null=True, blank=True)
    readable_id = models.CharField(null=True, max_length=255)
    live = models.BooleanField(default=False)

    def __str__(self):
        return self.title


class Course(TimestampedModel):
    """Model for a course"""

    program = models.ForeignKey(
        Program, on_delete=models.CASCADE, null=True, blank=True
    )
    position_in_program = models.PositiveSmallIntegerField(null=True, blank=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    thumbnail = models.ImageField(null=True, blank=True)
    readable_id = models.CharField(null=True, max_length=255)
    live = models.BooleanField(default=False)

    class Meta:
        ordering = ("program", "title")

    def save(self, *args, **kwargs):  # pylint: disable=arguments-differ
        """Overridden save method"""
        # If adding a Course to a Program without position specified, set it as the highest position + 1.
        # WARNING: This is open to a race condition. Two near-simultaneous queries could end up with
        #    the same position_in_program value for multiple Courses in one Program. This is very
        #    unlikely (adding courses will be an admin-only task, and the position can be explicitly
        #    provided), easily fixed, and the resulting bug would be very minor.
        if self.program and not self.position_in_program:
            last_position = (
                self.program.course_set.order_by("-position_in_program")
                .values_list("position_in_program", flat=True)
                .first()
            )
            self.position_in_program = 1 if not last_position else last_position + 1
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class CourseRun(TimestampedModel):
    """Model for a single run/instance of a course"""

    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    courseware_id = models.CharField(max_length=255, blank=True, null=True, unique=True)
    courseware_url_path = models.CharField(max_length=500, blank=True, null=True)
    start_date = models.DateTimeField(null=True, blank=True, db_index=True)
    end_date = models.DateTimeField(null=True, blank=True, db_index=True)
    enrollment_start = models.DateTimeField(null=True, blank=True, db_index=True)
    enrollment_end = models.DateTimeField(null=True, blank=True, db_index=True)
    live = models.BooleanField(default=False)

    def __str__(self):
        return self.title

    @property
    def courseware_url(self):
        """
        Full URL for this CourseRun as it exists in the courseware

        Returns:
            str or None: Full URL or None
        """
        return (
            edx_redirect_url(self.courseware_url_path)
            if self.courseware_url_path
            else None
        )
