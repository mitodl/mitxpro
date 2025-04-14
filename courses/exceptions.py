"""
Exceptions for courses
"""

from django.core.exceptions import ValidationError


class CourseRunDateValidationError(ValidationError):
    """ValidationError for when course run dates don't meet validation requirements."""
