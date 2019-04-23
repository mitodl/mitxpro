"""Wagtail page factories"""
import factory
import wagtail_factories

from cms.models import ProgramPage, CoursePage
from courses.factories import ProgramFactory, CourseFactory


class ProgramPageFactory(wagtail_factories.PageFactory):
    """ProgramPage factory class"""

    program = factory.SubFactory(ProgramFactory)
    subhead = factory.fuzzy.FuzzyText(prefix="Subhead ")
    thumbnail_image = factory.SubFactory(wagtail_factories.ImageFactory)

    class Meta:
        model = ProgramPage


class CoursePageFactory(wagtail_factories.PageFactory):
    """CoursePage factory class"""

    course = factory.SubFactory(CourseFactory)
    subhead = factory.fuzzy.FuzzyText(prefix="Subhead ")
    thumbnail_image = factory.SubFactory(wagtail_factories.ImageFactory)
    background_image = factory.SubFactory(wagtail_factories.ImageFactory)

    class Meta:
        model = CoursePage
