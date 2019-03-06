"""Factories for courses"""
import faker
import factory
from factory import fuzzy
from factory.django import DjangoModelFactory, ImageField

from courses.models import Course, CourseRun, Program

FAKE = faker.Factory.create()


class ProgramFactory(DjangoModelFactory):
    """Factory for Program"""

    title = fuzzy.FuzzyText(prefix="Program ")
    description = fuzzy.FuzzyText()
    thumbnail = ImageField()
    readable_id = factory.Sequence(lambda n: f"program_{n}")
    live = factory.Faker("boolean")

    class Meta:
        model = Program


class CourseFactory(DjangoModelFactory):
    """Factory for Course"""

    program = factory.SubFactory(ProgramFactory)
    position_in_program = factory.Sequence(lambda n: n)
    title = fuzzy.FuzzyText()
    description = fuzzy.FuzzyText()
    thumbnail = ImageField()
    readable_id = factory.Sequence(lambda n: f"course_{n}")
    live = factory.Faker("boolean")

    class Meta:
        model = Course


class CourseRunFactory(DjangoModelFactory):
    """Factory for CourseRun"""

    course = factory.SubFactory(CourseFactory)
    title = fuzzy.FuzzyText()
    courseware_id = factory.Sequence(lambda n: f"courserun_{n}")
    courseware_url = factory.Faker("url")
    start_date = factory.Faker("date_time_this_year")
    end_date = factory.Faker("date_time_this_year")
    enrollment_start = factory.Faker("date_time_this_year")
    enrollment_end = factory.Faker("date_time_this_year")
    live = factory.Faker("boolean")

    class Meta:
        model = CourseRun
