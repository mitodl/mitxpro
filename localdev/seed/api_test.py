"""Seed data API tests"""
# pylint: disable=unused-argument, redefined-outer-name
from types import SimpleNamespace
import pytest

from courses.models import Program, Course, CourseRun
from cms.models import ProgramPage, CoursePage
from localdev.seed.api import SeedDataLoader, get_raw_course_data_from_file


@pytest.fixture
def seeded():
    """Fixture for a scenario where course data has been loaded from our JSON file"""
    data = get_raw_course_data_from_file()
    seed_data_loader = SeedDataLoader()
    seed_data_loader.create_seed_data(data)
    return SimpleNamespace(raw_data=data, loader=seed_data_loader)


@pytest.mark.django_db
def test_seed_and_unseed_data(seeded):
    """Tests that the seed data functions can create and delete seed data"""
    expected_programs = len(seeded.raw_data["programs"])
    expected_courses = len(seeded.raw_data["courses"])
    expected_course_runs = sum(
        len(course_data.get("course_runs", []))
        for course_data in seeded.raw_data["courses"]
    )
    assert Program.objects.count() == expected_programs
    assert ProgramPage.objects.count() == expected_programs
    assert Course.objects.count() == expected_courses
    assert CoursePage.objects.count() == expected_courses
    assert CourseRun.objects.count() == expected_course_runs
    seeded.loader.delete_seed_data(seeded.raw_data)
    assert Program.objects.count() == 0
    assert ProgramPage.objects.count() == 0
    assert Course.objects.count() == 0
    assert CoursePage.objects.count() == 0
    assert CourseRun.objects.count() == 0


@pytest.mark.django_db
def test_seed_prefix(seeded):
    """
    Tests that the seed data functions add a prefix to a field values that indicates which objects are seed data
    """
    assert (
        Program.objects.exclude(
            title__startswith=SeedDataLoader.SEED_DATA_PREFIX
        ).exists()
        is False
    )
    assert (
        Course.objects.exclude(
            title__startswith=SeedDataLoader.SEED_DATA_PREFIX
        ).exists()
        is False
    )
    assert (
        CourseRun.objects.exclude(
            title__startswith=SeedDataLoader.SEED_DATA_PREFIX
        ).exists()
        is False
    )
