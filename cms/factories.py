"""Wagtail page factories"""
import pytz
from django.core.exceptions import ObjectDoesNotExist
from wagtail.core.rich_text import RichText

import factory
from factory.django import DjangoModelFactory
import faker
from faker.providers import internet
import wagtail_factories
from cms.blocks import (
    FacultyBlock,
    LearningTechniqueBlock,
    ResourceBlock,
    UserTestimonialBlock,
)
from cms.models import (
    CatalogPage,
    CertificatePage,
    CourseIndexPage,
    CoursePage,
    CoursesInProgramPage,
    ExternalCoursePage,
    ExternalProgramPage,
    FacultyMembersPage,
    ForTeamsPage,
    FrequentlyAskedQuestion,
    FrequentlyAskedQuestionPage,
    HomePage,
    ImageCarouselPage,
    LearningOutcomesPage,
    LearningTechniquesPage,
    NewsAndEventsBlock,
    NewsAndEventsPage,
    ProgramIndexPage,
    ProgramPage,
    ResourcePage,
    SignatoryPage,
    SiteNotification,
    TextSection,
    TextVideoSection,
    UserTestimonialsPage,
    WhoShouldEnrollPage,
)
from courses.factories import CourseFactory, ProgramFactory

factory.Faker.add_provider(internet)

FAKE = faker.Factory.create()


class CatalogPageFactory(wagtail_factories.PageFactory):
    """CatalogPage factory class"""

    class Meta:
        model = CatalogPage


class ProgramPageFactory(wagtail_factories.PageFactory):
    """ProgramPage factory class"""

    title = factory.Sequence("Test page - Program {0}".format)
    program = factory.SubFactory(ProgramFactory, page=None)
    subhead = factory.fuzzy.FuzzyText(prefix="Subhead ")
    thumbnail_image = factory.SubFactory(wagtail_factories.ImageFactory)
    background_image = factory.SubFactory(wagtail_factories.ImageFactory)

    certificate_page = factory.RelatedFactory(
        "cms.factories.CertificatePageFactory", "parent"
    )

    class Meta:
        model = ProgramPage

    @factory.post_generation
    def post_gen(obj, create, extracted, **kwargs):  # pylint:disable=unused-argument
        """Post-generation hook"""
        if create:
            # Move the created page to be a child of the program index page
            index_page = ProgramIndexPage.objects.first()
            if not index_page:
                raise ObjectDoesNotExist
            obj.move(index_page, "last-child")
            obj.refresh_from_db()
        return obj


class CoursePageFactory(wagtail_factories.PageFactory):
    """CoursePage factory class"""

    title = factory.Sequence("Test page - Course {0}".format)
    course = factory.SubFactory(CourseFactory, page=None)
    subhead = factory.fuzzy.FuzzyText(prefix="Subhead ")
    thumbnail_image = factory.SubFactory(wagtail_factories.ImageFactory)
    background_image = factory.SubFactory(wagtail_factories.ImageFactory)

    certificate_page = factory.RelatedFactory(
        "cms.factories.CertificatePageFactory", "parent"
    )

    class Meta:
        model = CoursePage

    @factory.post_generation
    def post_gen(obj, create, extracted, **kwargs):  # pylint:disable=unused-argument
        """Post-generation hook"""
        if create:
            # Move the created page to be a child of the course index page
            index_page = CourseIndexPage.objects.first()
            if not index_page:
                raise ObjectDoesNotExist
            obj.move(index_page, "last-child")
            obj.refresh_from_db()
        return obj


class ExternalCoursePageFactory(wagtail_factories.PageFactory):
    """ExternalCoursePage factory class"""

    title = factory.Sequence("Test page - External Course {0}".format)
    start_date = factory.Faker(
        "date_time_this_month", before_now=True, after_now=False, tzinfo=pytz.utc
    )
    price = factory.fuzzy.FuzzyDecimal(low=1, high=123)
    external_url = factory.Faker("uri")
    readable_id = factory.Sequence(
        lambda number: "external-course:/v{}/{}".format(number, FAKE.slug())
    )
    subhead = factory.fuzzy.FuzzyText(prefix="Subhead ")
    thumbnail_image = factory.SubFactory(wagtail_factories.ImageFactory)
    background_image = factory.SubFactory(wagtail_factories.ImageFactory)

    class Meta:
        model = ExternalCoursePage

    @factory.post_generation
    def post_gen(obj, create, extracted, **kwargs):  # pylint:disable=unused-argument
        """Post-generation hook"""
        if create:
            # Move the created page to be a child of the course index page
            index_page = CourseIndexPage.objects.first()
            if not index_page:
                raise ObjectDoesNotExist
            obj.move(index_page, "last-child")
            obj.refresh_from_db()
        return obj


class ExternalProgramPageFactory(wagtail_factories.PageFactory):
    """ExternalProgramPage factory class"""

    title = factory.Sequence("Test page - External Program {0}".format)
    start_date = factory.Faker(
        "date_time_this_month", before_now=True, after_now=False, tzinfo=pytz.utc
    )
    price = factory.fuzzy.FuzzyDecimal(low=1, high=123)
    external_url = factory.Faker("uri")
    readable_id = factory.Sequence(
        lambda number: "external-course:/v{}/{}".format(number, FAKE.slug())
    )
    subhead = factory.fuzzy.FuzzyText(prefix="Subhead ")
    thumbnail_image = factory.SubFactory(wagtail_factories.ImageFactory)
    background_image = factory.SubFactory(wagtail_factories.ImageFactory)
    course_count = factory.fuzzy.FuzzyInteger(1)

    class Meta:
        model = ExternalProgramPage

    @factory.post_generation
    def post_gen(obj, create, extracted, **kwargs):  # pylint:disable=unused-argument
        """Post-generation hook"""
        if create:
            # Move the created page to be a child of the program index page
            index_page = ProgramIndexPage.objects.first()
            if not index_page:
                raise ObjectDoesNotExist
            obj.move(index_page, "last-child")
            obj.refresh_from_db()
        return obj


class LearningOutcomesPageFactory(wagtail_factories.PageFactory):
    """LearningOutcomesPage factory class"""

    heading = factory.fuzzy.FuzzyText(prefix="heading ")
    sub_heading = factory.fuzzy.FuzzyText(prefix="Sub-heading ")
    outcome_items = factory.SubFactory(wagtail_factories.StreamFieldFactory)

    class Meta:
        model = LearningOutcomesPage


class LearningTechniquesItemFactory(wagtail_factories.StructBlockFactory):
    """LearningTechniquesItem factory class"""

    heading = factory.fuzzy.FuzzyText(prefix="heading ")
    sub_heading = factory.fuzzy.FuzzyText(prefix="Sub-heading ")
    image = factory.SubFactory(wagtail_factories.ImageFactory)

    class Meta:
        model = LearningTechniqueBlock


class LearningTechniquesPageFactory(wagtail_factories.PageFactory):
    """LearningTechniquesPage factory class"""

    technique_items = wagtail_factories.StreamFieldFactory(
        {"techniques": LearningTechniquesItemFactory}
    )

    class Meta:
        model = LearningTechniquesPage


class FrequentlyAskedQuestionPageFactory(wagtail_factories.PageFactory):
    """ FrequentlyAskedQuestionPage factory class"""

    class Meta:
        model = FrequentlyAskedQuestionPage


class FrequentlyAskedQuestionFactory(DjangoModelFactory):
    """FrequentlyAskedQuestion factory class"""

    faqs_page = factory.SubFactory(FrequentlyAskedQuestionPageFactory)
    question = factory.fuzzy.FuzzyText(prefix="question: ")
    answer = factory.fuzzy.FuzzyText(prefix="answer: ")

    class Meta:
        model = FrequentlyAskedQuestion


class ForTeamsPageFactory(wagtail_factories.PageFactory):
    """ForTeamsPage factory class"""

    content = factory.fuzzy.FuzzyText(prefix="Content ")
    action_title = factory.fuzzy.FuzzyText(prefix="Action title ")

    class Meta:
        model = ForTeamsPage


class TextSectionFactory(wagtail_factories.PageFactory):
    """TextSection factory class"""

    content = factory.fuzzy.FuzzyText(prefix="Content ")
    action_title = factory.fuzzy.FuzzyText(prefix="Action title ")
    action_url = factory.Faker("uri")

    class Meta:
        model = TextSection


class TextVideoSectionFactory(wagtail_factories.PageFactory):
    """TextVideoSection factory class"""

    content = factory.fuzzy.FuzzyText(prefix="Content ")
    action_title = factory.fuzzy.FuzzyText(prefix="Action title ")
    video_url = factory.fuzzy.FuzzyText(prefix="http://test.org/")

    class Meta:
        model = TextVideoSection


class WhoShouldEnrollPageFactory(wagtail_factories.PageFactory):
    """WhoShouldEnrollPage factory class"""

    image = factory.SubFactory(wagtail_factories.ImageFactory)
    content = factory.SubFactory(wagtail_factories.StreamFieldFactory)

    class Meta:
        model = WhoShouldEnrollPage


class CoursesInProgramPageFactory(wagtail_factories.PageFactory):
    """CoursesInProgramPage factory class"""

    heading = factory.fuzzy.FuzzyText(prefix="Heading ")
    body = factory.fuzzy.FuzzyText(prefix="Body ")
    contents = wagtail_factories.StreamFieldFactory({"item": CoursePageFactory})

    class Meta:
        model = CoursesInProgramPage


class ResourceBlockFactory(wagtail_factories.StructBlockFactory):
    """ResourceBlock factory class"""

    heading = factory.fuzzy.FuzzyText(prefix="Heading ")
    detail = factory.fuzzy.FuzzyText(prefix="Detail ")

    class Meta:
        model = ResourceBlock


class ResourcePageFactory(wagtail_factories.PageFactory):
    """ResourcePage factory class"""

    sub_heading = factory.fuzzy.FuzzyText(prefix="Sub heading ")
    content = wagtail_factories.StreamFieldFactory({"content": ResourceBlockFactory})

    class Meta:
        model = ResourcePage


# Cannot name TestimonialBlockFactory otherwise pytest will try to pick up as a test
class UserTestimonialBlockFactory(wagtail_factories.StructBlockFactory):
    """UserTestimonialBlock factory class"""

    name = factory.fuzzy.FuzzyText(prefix="name ")
    title = factory.fuzzy.FuzzyText(prefix="title ")
    image = factory.SubFactory(wagtail_factories.ImageFactory)
    quote = factory.fuzzy.FuzzyText(prefix="quote ")

    class Meta:
        model = UserTestimonialBlock


# Cannot name TestimonialPageFactory otherwise pytest will try to pick up as a test
class UserTestimonialsPageFactory(wagtail_factories.PageFactory):
    """UserTestimonialsPage factory class"""

    heading = factory.fuzzy.FuzzyText(prefix="heading ")
    subhead = factory.fuzzy.FuzzyText(prefix="subhead ")
    items = wagtail_factories.StreamFieldFactory(
        {"testimonial": UserTestimonialBlockFactory}
    )

    class Meta:
        model = UserTestimonialsPage


class NewsAndEventsBlockFactory(wagtail_factories.StructBlockFactory):
    """NewsAndEventsBlock factory class"""

    content_type = factory.fuzzy.FuzzyText(prefix="content_type ")
    title = factory.fuzzy.FuzzyText(prefix="title ")
    image = factory.SubFactory(wagtail_factories.ImageFactory)
    content = factory.fuzzy.FuzzyText(prefix="content ")
    call_to_action = factory.fuzzy.FuzzyText(prefix="call_to_action ")
    action_url = factory.Faker("uri")

    class Meta:
        model = NewsAndEventsBlock


class NewsAndEventsPageFactory(wagtail_factories.PageFactory):
    """NewsAndEventsPage factory class"""

    heading = factory.fuzzy.FuzzyText(prefix="heading ")
    items = wagtail_factories.StreamFieldFactory(
        {"news_and_events": NewsAndEventsBlockFactory}
    )

    class Meta:
        model = NewsAndEventsPage


class FacultyBlockFactory(wagtail_factories.StructBlockFactory):
    """FacultyBlock factory class"""

    name = factory.Faker("name")
    image = factory.SubFactory(wagtail_factories.ImageFactory)
    text = factory.LazyFunction(lambda: RichText("<p>{}</p>".format(FAKE.paragraph())))

    class Meta:
        model = FacultyBlock


class FacultyMembersPageFactory(wagtail_factories.PageFactory):
    """FacultyMembersPage factory class"""

    heading = factory.fuzzy.FuzzyText(prefix="heading ")
    subhead = factory.fuzzy.FuzzyText(prefix="subhead ")
    members = wagtail_factories.StreamFieldFactory({"member": FacultyBlockFactory})

    class Meta:
        model = FacultyMembersPage


class SiteNotificationFactory(DjangoModelFactory):
    """SiteNotification factory class"""

    message = factory.fuzzy.FuzzyText(prefix="message ")

    class Meta:
        model = SiteNotification


class ImageCarouselPageFactory(wagtail_factories.PageFactory):
    """ImageCarouselPage factory class"""

    title = factory.fuzzy.FuzzyText(prefix="title")
    images = wagtail_factories.StreamFieldFactory(
        {"image": wagtail_factories.ImageChooserBlockFactory}
    )

    class Meta:
        model = ImageCarouselPage


class HomePageFactory(wagtail_factories.PageFactory):
    """HomePage factory class"""

    title = factory.fuzzy.FuzzyText(prefix="Home ")
    subhead = factory.fuzzy.FuzzyText(prefix="Subhead ")

    class Meta:
        model = HomePage


class CourseIndexPageFactory(wagtail_factories.PageFactory):
    """CourseIndexPage factory class"""

    title = factory.fuzzy.FuzzyText(prefix="Course Index ")

    class Meta:
        model = CourseIndexPage


class ProgramIndexPageFactory(wagtail_factories.PageFactory):
    """ProgramIndexPage factory class"""

    title = factory.fuzzy.FuzzyText(prefix="Program Index ")

    class Meta:
        model = ProgramIndexPage


class SignatoryPageFactory(wagtail_factories.PageFactory):
    """SignatoryPage factory class"""

    name = factory.fuzzy.FuzzyText(prefix="Name")
    title_1 = factory.fuzzy.FuzzyText(prefix="Title_1")
    title_2 = factory.fuzzy.FuzzyText(prefix="Title_2")
    organization = factory.fuzzy.FuzzyText(prefix="Organization")
    signature_image = factory.SubFactory(wagtail_factories.ImageFactory)

    class Meta:
        model = SignatoryPage


class CertificatePageFactory(wagtail_factories.PageFactory):
    """CertificatePage factory class"""

    product_name = factory.fuzzy.FuzzyText(prefix="product_name")
    CEUs = factory.Faker("pystr_format", string_format="#.#")
    signatories = wagtail_factories.StreamFieldFactory(
        {"signatory": SignatoryPageFactory}
    )

    class Meta:
        model = CertificatePage
