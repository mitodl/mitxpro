"""Factories for creating course data in tests"""

from datetime import UTC, timedelta

import factory
import faker
from factory import SubFactory, Trait, fuzzy
from factory.django import DjangoModelFactory
from factory.fuzzy import FuzzyText

from courses.constants import PROGRAM_TEXT_ID_PREFIX
from ecommerce.models import Company
from users.factories import UserFactory

from .models import (
    Course,
    CourseLanguage,
    CourseRun,
    CourseRunCertificate,
    CourseRunEnrollment,
    CourseRunGrade,
    CourseTopic,
    Platform,
    Program,
    ProgramCertificate,
    ProgramEnrollment,
    ProgramRun,
)

FAKE = faker.Factory.create()


class CompanyFactory(DjangoModelFactory):
    """Factory for Company"""

    name = factory.Faker("company")

    class Meta:
        model = Company


class CourseLanguageFactory(DjangoModelFactory):
    """Factory for Course Language"""

    name = factory.Sequence(lambda n: f"Language_{n}")

    class Meta:
        model = CourseLanguage


class PlatformFactory(DjangoModelFactory):
    """Factory for Platform"""

    name = FuzzyText(prefix="Platform-", length=100)

    class Meta:
        model = Platform


class ProgramFactory(DjangoModelFactory):
    """Factory for Programs"""

    title = fuzzy.FuzzyText(prefix="Program ")
    readable_id = factory.Sequence(lambda number: f"{PROGRAM_TEXT_ID_PREFIX}{number}")
    platform = factory.SubFactory(PlatformFactory)
    live = True

    page = factory.RelatedFactory("cms.factories.ProgramPageFactory", "program")

    class Meta:
        model = Program


class ProgramRunFactory(DjangoModelFactory):
    """Factory for ProgramRuns"""

    program = factory.SubFactory(ProgramFactory)
    run_tag = factory.Sequence("R{}".format)

    class Meta:
        model = ProgramRun


class CourseFactory(DjangoModelFactory):
    """Factory for Courses"""

    program = factory.SubFactory(ProgramFactory)
    position_in_program = None  # will get populated in save()
    title = fuzzy.FuzzyText(prefix="Course ")
    readable_id = factory.Sequence("course-{}".format)
    platform = factory.SubFactory(PlatformFactory)
    live = True

    page = factory.RelatedFactory("cms.factories.CoursePageFactory", "course")

    class Meta:
        model = Course

    class Params:
        no_program = factory.Trait(program=None, position_in_program=None)


class CourseRunFactory(DjangoModelFactory):
    """Factory for CourseRuns"""

    course = factory.SubFactory(CourseFactory)
    title = factory.LazyAttribute(lambda x: "CourseRun " + FAKE.sentence())  # noqa: ARG005
    courseware_id = factory.Sequence(lambda number: f"course:v{number}+{FAKE.slug()}")
    run_tag = factory.Sequence("R{}".format)
    courseware_url_path = factory.Faker("uri")
    start_date = factory.Faker(
        "date_time_this_month", before_now=True, after_now=False, tzinfo=UTC
    )
    end_date = factory.LazyAttribute(
        lambda obj: obj.start_date + timedelta(days=30) if obj.start_date else None
    )
    enrollment_start = factory.Faker(
        "date_time_this_month", before_now=True, after_now=False, tzinfo=UTC
    )
    enrollment_end = factory.Faker(
        "date_time_this_month", before_now=False, after_now=True, tzinfo=UTC
    )
    expiration_date = factory.Faker(
        "date_time_between", start_date="+1y", end_date="+2y", tzinfo=UTC
    )
    live = True

    class Meta:
        model = CourseRun

    class Params:
        past_start = factory.Trait(
            start_date=factory.Faker("past_datetime", tzinfo=UTC)
        )
        past_enrollment_end = factory.Trait(
            enrollment_end=factory.Faker("past_datetime", tzinfo=UTC),
            enrollment_start=factory.LazyAttribute(
                lambda obj: obj.enrollment_end - timedelta(days=1)
            ),
        )

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """Allow creating test objects without validation."""
        force_insert = kwargs.pop("force_insert", False)
        obj = model_class(*args, **kwargs)

        if not force_insert:
            obj.save()
        else:
            # Directly insert into DB without triggering save()
            model_class.objects.bulk_create([obj])

        return obj


class CourseRunCertificateFactory(DjangoModelFactory):
    """Factory for CourseRunCertificate"""

    course_run = factory.SubFactory(CourseRunFactory)
    user = factory.SubFactory(UserFactory)

    class Meta:
        model = CourseRunCertificate


class CourseRunGradeFactory(DjangoModelFactory):
    """Factory for CourseRunGrade"""

    course_run = factory.SubFactory(CourseRunFactory)
    user = factory.SubFactory(UserFactory)
    grade = factory.fuzzy.FuzzyDecimal(low=0.0, high=1.0)
    letter_grade = factory.fuzzy.FuzzyText(length=1)
    passed = factory.fuzzy.FuzzyChoice([True, False])
    set_by_admin = factory.fuzzy.FuzzyChoice([True, False])

    class Meta:
        model = CourseRunGrade


class CourseTopicFactory(DjangoModelFactory):
    """Factory for CourseTopic"""

    name = fuzzy.FuzzyText(prefix="Topic ")
    parent = None

    class Meta:
        model = CourseTopic


class ProgramCertificateFactory(DjangoModelFactory):
    """Factory for ProgramCertificate"""

    program = factory.SubFactory(ProgramFactory)
    user = factory.SubFactory(UserFactory)

    class Meta:
        model = ProgramCertificate


class CourseRunEnrollmentFactory(DjangoModelFactory):
    """Factory for CourseRunEnrollment"""

    user = SubFactory(UserFactory)
    run = SubFactory(CourseRunFactory)
    order = SubFactory("ecommerce.factories.OrderFactory")

    class Params:
        has_company_affiliation = Trait(company=SubFactory(CompanyFactory))

    class Meta:
        model = CourseRunEnrollment


class ProgramEnrollmentFactory(DjangoModelFactory):
    """Factory for ProgramEnrollment"""

    user = SubFactory(UserFactory)
    program = SubFactory(ProgramFactory)
    order = SubFactory("ecommerce.factories.OrderFactory")

    class Params:
        has_company_affiliation = Trait(company=SubFactory(CompanyFactory))

    class Meta:
        model = ProgramEnrollment
