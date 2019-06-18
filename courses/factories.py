"""Factories for creating course data in tests"""
import pytz
import faker
import factory
from factory import fuzzy, SubFactory, Trait
from factory.django import DjangoModelFactory

from ecommerce.models import Company
from users.factories import UserFactory

from .models import Program, Course, CourseRun, ProgramEnrollment, CourseRunEnrollment

FAKE = faker.Factory.create()


class CompanyFactory(DjangoModelFactory):
    """Factory for Company"""

    name = factory.Faker("company")

    class Meta:
        model = Company


class ProgramFactory(DjangoModelFactory):
    """Factory for Programs"""

    title = fuzzy.FuzzyText(prefix="Program ")
    readable_id = factory.Sequence("program-{0}".format)
    live = factory.Faker("boolean")

    class Meta:
        model = Program


class CourseFactory(DjangoModelFactory):
    """Factory for Courses"""

    program = factory.SubFactory(ProgramFactory)
    position_in_program = factory.Sequence(lambda n: n)
    title = fuzzy.FuzzyText(prefix="Course ")
    readable_id = factory.Sequence("course-{0}".format)
    live = factory.Faker("boolean")

    class Meta:
        model = Course

    class Params:
        no_program = factory.Trait(program=None, position_in_program=None)


class CourseRunFactory(DjangoModelFactory):
    """Factory for CourseRuns"""

    course = factory.SubFactory(CourseFactory)
    title = factory.LazyAttribute(lambda x: "CourseRun " + FAKE.sentence())
    courseware_id = factory.Sequence(
        lambda number: "course:/v{}/{}".format(number, FAKE.slug())
    )
    courseware_url_path = factory.Faker("uri")
    start_date = factory.Faker(
        "date_time_this_month", before_now=True, after_now=False, tzinfo=pytz.utc
    )
    end_date = factory.Faker(
        "date_time_this_year", before_now=False, after_now=True, tzinfo=pytz.utc
    )
    enrollment_start = factory.Faker(
        "date_time_this_month", before_now=True, after_now=False, tzinfo=pytz.utc
    )
    enrollment_end = factory.Faker(
        "date_time_this_month", before_now=False, after_now=True, tzinfo=pytz.utc
    )
    live = factory.Faker("boolean")

    class Meta:
        model = CourseRun

    class Params:
        past_start = factory.Trait(
            start_date=factory.Faker("past_datetime", tzinfo=pytz.utc)
        )


class CourseRunEnrollmentFactory(DjangoModelFactory):
    """Factory for CourseRunEnrollment"""

    user = SubFactory(UserFactory)
    run = SubFactory(CourseRunFactory)

    class Params:
        has_company_affiliation = Trait(company=SubFactory(CompanyFactory))

    class Meta:
        model = CourseRunEnrollment


class ProgramEnrollmentFactory(DjangoModelFactory):
    """Factory for ProgramEnrollment"""

    user = SubFactory(UserFactory)
    program = SubFactory(ProgramFactory)

    class Params:
        has_company_affiliation = Trait(company=SubFactory(CompanyFactory))

    class Meta:
        model = ProgramEnrollment
