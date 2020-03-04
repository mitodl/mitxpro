"""Seed data API tests"""
# pylint: disable=unused-argument, redefined-outer-name
from types import SimpleNamespace
import pytest

from courses.models import Program, Course, CourseRun, CourseTopic
from cms.models import ProgramPage, CoursePage, ResourcePage
from ecommerce.models import Product, ProductVersion
from ecommerce.test_utils import unprotect_version_tables
from localdev.seed.api import SeedDataLoader, get_raw_seed_data_from_file


@pytest.fixture
def seeded(settings):
    """Fixture for a scenario where course data has been loaded from our JSON file"""
    settings.VOUCHER_DOMESTIC_EMPLOYEE_KEY = ""
    settings.VOUCHER_DOMESTIC_EMPLOYEE_ID_KEY = None
    delattr(settings, "VOUCHER_COMPANY_ID")
    data = get_raw_seed_data_from_file()
    seed_data_loader = SeedDataLoader()
    seed_data_loader.create_seed_data(data)
    return SimpleNamespace(raw_data=data, loader=seed_data_loader)


@pytest.mark.django_db
def test_seed_prefix(seeded):
    """
    Tests that the seed data functions add a prefix to a field values that indicates which objects are seed data
    """
    # Test helper functions
    seeded_value = seeded.loader.seed_prefixed("Some Title")
    assert seeded_value == "{} Some Title".format(SeedDataLoader.SEED_DATA_PREFIX)
    assert seeded.loader.is_seed_value(seeded_value) is True
    # Test saved object titles
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


@pytest.mark.django_db
def test_seed_and_unseed_data(seeded):
    """Tests that the seed data functions can create and delete seed data"""
    expected_programs = len(seeded.raw_data["programs"])
    expected_courses = len(seeded.raw_data["courses"])
    expected_course_runs = sum(
        len(course_data.get("course_runs", []))
        for course_data in seeded.raw_data["courses"]
    )
    # Hardcoding this value since it would be annoying to check for it programatically
    expected_products = 12
    expected_resource_pages = len(seeded.raw_data["resource_pages"])
    assert Program.objects.count() == expected_programs
    assert ProgramPage.objects.count() == expected_programs
    assert Course.objects.count() == expected_courses
    assert CoursePage.objects.count() == expected_courses
    assert CourseRun.objects.count() == expected_course_runs
    assert ResourcePage.objects.count() == expected_resource_pages
    assert Product.objects.count() == expected_products
    assert ProductVersion.objects.count() == expected_products

    with unprotect_version_tables():
        seeded.loader.delete_seed_data(seeded.raw_data)
    assert Program.objects.count() == 0
    assert ProgramPage.objects.count() == 0
    assert Course.objects.count() == 0
    assert CoursePage.objects.count() == 0
    assert CourseRun.objects.count() == 0
    assert ResourcePage.objects.count() == 0
    assert Product.objects.count() == 0
    assert ProductVersion.objects.count() == 0


@pytest.mark.django_db
def test_topics(seeded):
    """Tests that the seed data functions can deserialize topics"""
    for course_data in seeded.raw_data["courses"]:
        course = Course.objects.get(readable_id=course_data["readable_id"])
        topics = [
            {"name": topic.name} for topic in CourseTopic.objects.filter(course=course)
        ]

        def name_key(topic):
            """Helper function to get a name for sorting purporses"""
            return topic["name"]

        assert sorted(topics, key=name_key) == sorted(
            course_data["topics"], key=name_key
        )

    before_count = CourseTopic.objects.count()

    with unprotect_version_tables():
        seeded.loader.delete_seed_data(seeded.raw_data)
    # unseeding will not cause topics to be deleted since they could be referenced by other courses
    assert CourseTopic.objects.count() == before_count
