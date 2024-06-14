"""
Sync external course API tests
"""

import pytest

from courses.sync_external_courses.api import (
    generate_emeritus_course_run_tag,
    generate_external_course_run_courseware_id,
)


@pytest.mark.parametrize(
    ("emeritus_course_run_code", "expected_course_run_tag"),
    [
        ("MO-EOB-18-01#1", "18-01#1"),
        ("MO-EOB-08-01#1", "08-01#1"),
        ("MO-EOB-08-12#1", "08-12#1"),
        ("MO-EOB-18-01#12", "18-01#12"),
        ("MO-EOB-18-01#212", "18-01#212"),
    ],
)
def test_generate_emeritus_course_run_tag(
    emeritus_course_run_code, expected_course_run_tag
):
    """
    Tests that `generate_emeritus_course_run_tag` generates the expected course tag for Emeritus Course Run Codes.
    """
    assert (
        generate_emeritus_course_run_tag(emeritus_course_run_code)
        == expected_course_run_tag
    )


@pytest.mark.parametrize(
    ("course_readable_id", "course_run_tag", "expected_course_run_courseware_id"),
    [
        ("course-v1:xPRO+EOB", "18-01#1", "course-v1:xPRO+EOB+18-01#1"),
        ("course-v1:xPRO+EOB", "08-01#1", "course-v1:xPRO+EOB+08-01#1"),
        ("course-v1:xPRO+EOB", "18-01#12", "course-v1:xPRO+EOB+18-01#12"),
        ("course-v1:xPRO+EOB", "18-01#212", "course-v1:xPRO+EOB+18-01#212"),
    ],
)
def test_generate_external_course_run_courseware_id(
    course_readable_id, course_run_tag, expected_course_run_courseware_id
):
    """
    Test that `generate_external_course_run_courseware_id` returns the expected courseware_id for the given
    course run tag and course readable id.
    """
    assert (
        generate_external_course_run_courseware_id(course_run_tag, course_readable_id)
        == expected_course_run_courseware_id
    )
