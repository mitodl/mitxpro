"""Wagtail page factories"""

import factory
import faker
import wagtail_factories
from django.core.exceptions import ObjectDoesNotExist
from factory.django import DjangoModelFactory
from faker.providers import internet
from wagtail.rich_text import RichText

from cms.blocks import (
    FacultyBlock,
    LearningTechniqueBlock,
    ResourceBlock,
    SuccessStoriesBlock,
    UserTestimonialBlock,
)
from cms.constants import COMMON_COURSEWARE_COMPONENT_INDEX_SLUG, UPCOMING_WEBINAR
from cms.models import (
    BlogIndexPage,
    CatalogPage,
    CertificatePage,
    CommonComponentIndexPage,
    CompaniesLogoCarouselSection,
    CourseIndexPage,
    CourseOverviewPage,
    CoursePage,
    CoursesInProgramPage,
    EnterprisePage,
    ExternalCoursePage,
    ExternalProgramPage,
    FacultyMembersPage,
    ForTeamsCommonPage,
    ForTeamsPage,
    FrequentlyAskedQuestion,
    FrequentlyAskedQuestionPage,
    HomePage,
    ImageCarouselPage,
    LearningJourneySection,
    LearningOutcomesPage,
    LearningStrategyFormSection,
    LearningTechniquesCommonPage,
    LearningTechniquesPage,
    NewsAndEventsBlock,
    NewsAndEventsPage,
    ProgramIndexPage,
    ProgramPage,
    ResourcePage,
    SignatoryPage,
    SiteNotification,
    SuccessStoriesSection,
    TextSection,
    TextVideoSection,
    UserTestimonialsPage,
    WebinarIndexPage,
    WebinarPage,
    WhoShouldEnrollPage,
)
from courses.factories import (
    CourseFactory,
    CourseLanguageFactory,
    PlatformFactory,
    ProgramFactory,
)

factory.Faker.add_provider(internet)

FAKE = faker.Factory.create()


class CatalogPageFactory(wagtail_factories.PageFactory):
    """CatalogPage factory class"""

    class Meta:
        model = CatalogPage


class ProgramPageFactory(wagtail_factories.PageFactory):
    """ProgramPage factory class"""

    title = factory.Sequence("Test page - Program {}".format)
    program = factory.SubFactory(ProgramFactory, page=None)
    subhead = factory.fuzzy.FuzzyText(prefix="Subhead ")
    thumbnail_image = factory.SubFactory(wagtail_factories.ImageFactory)
    background_image = factory.SubFactory(wagtail_factories.ImageFactory)
    language = factory.SubFactory(CourseLanguageFactory)
    parent = factory.SubFactory(wagtail_factories.PageFactory)
    certificate_page = factory.RelatedFactory(
        "cms.factories.CertificatePageFactory", "parent"
    )
    live = True

    class Meta:
        model = ProgramPage

    @factory.post_generation
    def post_gen(obj, create, extracted, **kwargs):  # noqa: ARG002, N805
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

    title = factory.Sequence("Test page - Course {}".format)
    course = factory.SubFactory(CourseFactory, page=None)
    subhead = factory.fuzzy.FuzzyText(prefix="Subhead ")
    thumbnail_image = factory.SubFactory(wagtail_factories.ImageFactory)
    background_image = factory.SubFactory(wagtail_factories.ImageFactory)
    language = factory.SubFactory(CourseLanguageFactory)
    parent = factory.SubFactory(wagtail_factories.PageFactory)
    certificate_page = factory.RelatedFactory(
        "cms.factories.CertificatePageFactory", "parent"
    )
    live = True

    class Meta:
        model = CoursePage

    @factory.post_generation
    def post_gen(obj, create, extracted, **kwargs):  # noqa: ARG002, N805
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

    course = factory.SubFactory(CourseFactory, page=None)

    title = factory.Sequence("Test page - External Course {}".format)
    external_marketing_url = factory.Faker("uri")
    marketing_hubspot_form_id = factory.Faker("bothify", text="??????????")
    subhead = factory.fuzzy.FuzzyText(prefix="Subhead ")
    thumbnail_image = factory.SubFactory(wagtail_factories.ImageFactory)
    background_image = factory.SubFactory(wagtail_factories.ImageFactory)
    language = factory.SubFactory(CourseLanguageFactory)
    parent = factory.SubFactory(wagtail_factories.PageFactory)

    class Meta:
        model = ExternalCoursePage

    @factory.post_generation
    def post_gen(obj, create, extracted, **kwargs):  # noqa: ARG002, N805
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

    program = factory.SubFactory(ProgramFactory, page=None)

    title = factory.Sequence("Test page - External Program {}".format)
    external_marketing_url = factory.Faker("uri")
    marketing_hubspot_form_id = factory.Faker("bothify", text="??????????")
    subhead = factory.fuzzy.FuzzyText(prefix="Subhead ")
    thumbnail_image = factory.SubFactory(wagtail_factories.ImageFactory)
    background_image = factory.SubFactory(wagtail_factories.ImageFactory)
    language = factory.SubFactory(CourseLanguageFactory)
    parent = factory.SubFactory(wagtail_factories.PageFactory)

    class Meta:
        model = ExternalProgramPage

    @factory.post_generation
    def post_gen(obj, create, extracted, **kwargs):  # noqa: ARG002, N805
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
    image = factory.SubFactory(wagtail_factories.ImageChooserBlockFactory)

    class Meta:
        model = LearningTechniqueBlock


class LearningTechniquesPageFactory(wagtail_factories.PageFactory):
    """LearningTechniquesPage factory class"""

    technique_items = wagtail_factories.StreamFieldFactory(
        {"techniques": factory.SubFactory(LearningTechniquesItemFactory)}
    )

    class Meta:
        model = LearningTechniquesPage


class FrequentlyAskedQuestionPageFactory(wagtail_factories.PageFactory):
    """FrequentlyAskedQuestionPage factory class"""

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


class CoursePageChooserBlockFactory(wagtail_factories.PageChooserBlockFactory):
    """CoursePage chooser factory"""

    class Meta:
        model = CoursePage


class CoursesInProgramPageFactory(wagtail_factories.PageFactory):
    """CoursesInProgramPage factory class"""

    heading = factory.fuzzy.FuzzyText(prefix="Heading ")
    body = factory.fuzzy.FuzzyText(prefix="Body ")
    contents = wagtail_factories.StreamFieldFactory(
        {"item": factory.SubFactory(CoursePageChooserBlockFactory)}
    )

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
    image = factory.SubFactory(wagtail_factories.ImageChooserBlockFactory)
    quote = factory.fuzzy.FuzzyText(prefix="quote ")

    class Meta:
        model = UserTestimonialBlock


# Cannot name TestimonialPageFactory otherwise pytest will try to pick up as a test
class UserTestimonialsPageFactory(wagtail_factories.PageFactory):
    """UserTestimonialsPage factory class"""

    heading = factory.fuzzy.FuzzyText(prefix="heading ")
    subhead = factory.fuzzy.FuzzyText(prefix="subhead ")
    items = wagtail_factories.StreamFieldFactory(
        {"testimonial": factory.SubFactory(UserTestimonialBlockFactory)}
    )

    class Meta:
        model = UserTestimonialsPage


class NewsAndEventsBlockFactory(wagtail_factories.StructBlockFactory):
    """NewsAndEventsBlock factory class"""

    content_type = factory.fuzzy.FuzzyText(prefix="content_type ")
    title = factory.fuzzy.FuzzyText(prefix="title ")
    image = factory.SubFactory(wagtail_factories.ImageChooserBlockFactory)
    content = factory.fuzzy.FuzzyText(prefix="content ")
    call_to_action = factory.fuzzy.FuzzyText(prefix="call_to_action ")
    action_url = factory.Faker("uri")

    class Meta:
        model = NewsAndEventsBlock


class NewsAndEventsPageFactory(wagtail_factories.PageFactory):
    """NewsAndEventsPage factory class"""

    heading = factory.fuzzy.FuzzyText(prefix="heading ")
    items = wagtail_factories.StreamFieldFactory(
        {"news_and_events": factory.SubFactory(NewsAndEventsBlockFactory)}
    )

    class Meta:
        model = NewsAndEventsPage


class FacultyBlockFactory(wagtail_factories.StructBlockFactory):
    """FacultyBlock factory class"""

    name = factory.Faker("name")
    image = factory.SubFactory(wagtail_factories.ImageChooserBlockFactory)
    description = factory.LazyFunction(lambda: RichText(f"<p>{FAKE.paragraph()}</p>"))

    class Meta:
        model = FacultyBlock


class FacultyMembersPageFactory(wagtail_factories.PageFactory):
    """FacultyMembersPage factory class"""

    heading = factory.fuzzy.FuzzyText(prefix="heading ")
    subhead = factory.fuzzy.FuzzyText(prefix="subhead ")
    members = wagtail_factories.StreamFieldFactory(
        {"member": factory.SubFactory(FacultyBlockFactory)}
    )

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
        {"image": factory.SubFactory(wagtail_factories.ImageChooserBlockFactory)}
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
    signature_image = factory.SubFactory(wagtail_factories.ImageChooserBlockFactory)

    class Meta:
        model = SignatoryPage


class SignatoryChooserBlockFactory(wagtail_factories.PageChooserBlockFactory):
    class Meta:
        model = SignatoryPage


class CertificatePageFactory(wagtail_factories.PageFactory):
    """CertificatePage factory class"""

    product_name = factory.fuzzy.FuzzyText(prefix="product_name")
    CEUs = factory.fuzzy.FuzzyDecimal(low=1, high=10, precision=2)
    partner_logo = factory.SubFactory(wagtail_factories.ImageChooserBlockFactory)
    signatories = wagtail_factories.StreamFieldFactory(
        {"signatory": factory.SubFactory(SignatoryChooserBlockFactory)}
    )

    class Meta:
        model = CertificatePage


class WebinarIndexPageFactory(wagtail_factories.PageFactory):
    """WebinarIndexPage factory"""

    class Meta:
        model = WebinarIndexPage


class WebinarPageFactory(wagtail_factories.PageFactory):
    """WebinarPage factory class"""

    title = factory.fuzzy.FuzzyText(prefix="Webinar ")
    course = factory.SubFactory(CourseFactory)
    category = UPCOMING_WEBINAR
    sub_heading = factory.fuzzy.FuzzyText()
    banner_image = factory.SubFactory(wagtail_factories.ImageFactory)
    date = factory.Faker("future_date")
    time = "11 AM - 12 PM ET"
    description = factory.fuzzy.FuzzyText()
    action_url = factory.Faker("uri")
    parent = factory.SubFactory(WebinarIndexPageFactory)
    live = True

    class Meta:
        model = WebinarPage


class BlogIndexPageFactory(wagtail_factories.PageFactory):
    """BlogIndexPage factory"""

    class Meta:
        model = BlogIndexPage


class EnterprisePageFactory(wagtail_factories.PageFactory):
    """EnterprisePage factory"""

    class Meta:
        model = EnterprisePage


class CompaniesLogoCarouselPageFactory(wagtail_factories.PageFactory):
    """CompaniesLogoCarouselPage factory class"""

    heading = factory.fuzzy.FuzzyText(prefix="heading")
    images = wagtail_factories.StreamFieldFactory(
        {"image": factory.SubFactory(wagtail_factories.ImageChooserBlockFactory)}
    )

    class Meta:
        model = CompaniesLogoCarouselSection


class LearningJourneyPageFactory(wagtail_factories.PageFactory):
    """LearningJourneyPage factory class"""

    heading = factory.fuzzy.FuzzyText(prefix="heading ")
    description = factory.fuzzy.FuzzyText()
    journey_image = factory.SubFactory(wagtail_factories.ImageFactory)
    journey_items = factory.SubFactory(wagtail_factories.StreamFieldFactory)
    call_to_action = factory.fuzzy.FuzzyText(prefix="call_to_action ")
    action_url = factory.Faker("uri")
    pdf_file = factory.SubFactory(wagtail_factories.DocumentFactory)

    class Meta:
        model = LearningJourneySection


class SuccessStoriesBlockFactory(wagtail_factories.StructBlockFactory):
    """SuccessStoriesBlock factory class"""

    title = factory.fuzzy.FuzzyText(prefix="title ")
    image = factory.SubFactory(wagtail_factories.ImageChooserBlockFactory)
    content = factory.fuzzy.FuzzyText(prefix="content ")
    call_to_action = factory.fuzzy.FuzzyText(prefix="call_to_action ")
    action_url = factory.Faker("uri")

    class Meta:
        model = SuccessStoriesBlock


class SuccessStoriesPageFactory(wagtail_factories.PageFactory):
    """SuccessStoriesPage factory class"""

    heading = factory.fuzzy.FuzzyText(prefix="heading ")
    subhead = factory.fuzzy.FuzzyText(prefix="Subhead ")
    success_stories = wagtail_factories.StreamFieldFactory(
        {"success_story": factory.SubFactory(SuccessStoriesBlockFactory)}
    )

    class Meta:
        model = SuccessStoriesSection


class LearningStrategyFormPageFactory(wagtail_factories.PageFactory):
    """LearningStrategyForm factory class"""

    heading = factory.fuzzy.FuzzyText(prefix="heading ")
    subhead = factory.fuzzy.FuzzyText(prefix="Subhead ")

    class Meta:
        model = LearningStrategyFormSection


class CourseOverviewPageFactory(wagtail_factories.PageFactory):
    """CourseOverviewPage factory class"""

    heading = factory.fuzzy.FuzzyText(prefix="heading ")
    overview = factory.LazyFunction(lambda: RichText(f"<p>{FAKE.paragraph()}</p>"))

    class Meta:
        model = CourseOverviewPage


class CommonComponentIndexPageFactory(wagtail_factories.PageFactory):
    """CommonComponentIndexPage factory class"""

    title = factory.fuzzy.FuzzyText()
    slug = COMMON_COURSEWARE_COMPONENT_INDEX_SLUG

    class Meta:
        model = CommonComponentIndexPage


class LearningTechniqueCommonPageFactory(LearningTechniquesPageFactory):
    """LearningTechniquesCommonPage factory class"""

    platform = factory.SubFactory(PlatformFactory)
    title = factory.fuzzy.FuzzyText()

    class Meta:
        model = LearningTechniquesCommonPage


class ForTeamsCommonPageFactory(ForTeamsPageFactory):
    """ForTeamsCommonPage factory class"""

    platform = factory.SubFactory(PlatformFactory)
    title = factory.fuzzy.FuzzyText()

    class Meta:
        model = ForTeamsCommonPage
