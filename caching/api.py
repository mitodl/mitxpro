"""
Interface for Django's caching API
"""
from dill import dumps, loads
from django.core.cache import cache
from django.db.models import Prefetch

from courses.models import Course
from ecommerce.models import Product


def get_course_key(course_id):
    """
    Generates cache key for a course id.

    Args:
        course_id (int): id of a course.

    Returns:
        str: Cache for the given course id.
    """
    return f"course_id:{course_id}"


def get_course_with_related_objects(course_id):
    """
    Gets course with related objects from cache if it is available
    else fetch the course with related objects and add it to the cache.

    Args:
        course_id (int): id of a course.

    Returns:
        Course or None: Course with related objects or None.
    """
    cache_key = get_course_key(course_id)
    course = cache.get(cache_key)
    course = loads(course) if course else None
    print("\n\n\nCOURSE FROM CACHE:", course)

    if not course:
        course = (
            Course.objects.filter(id=course_id)
            .select_related("program", "program__programpage")
            .prefetch_related(
                "courseruns",
                Prefetch(
                    "courseruns__products", Product.objects.with_ordered_versions()
                ),
            ).first()
        )
        if course:
            print("\n\n\nAdding Course Cache for:", course_id)
            cache.set(cache_key, dumps(course), 24 * 60 * 60)

    return course


def invalidate_course_cache(course_id):
    cache_key = get_course_key(course_id)
    cache.delete(cache_key)
