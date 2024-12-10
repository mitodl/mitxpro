import pytest

from cms.factories import (
    CommonComponentIndexPageFactory,
    CoursePageFactory,
    ExternalCoursePageFactory,
    ForTeamsCommonPageFactory,
    LearningTechniqueCommonPageFactory,
    PlatformFactory,
)
from cms.models import (
    ForTeamsCommonPage,
    ForTeamsPage,
    LearningTechniquesCommonPage,
    LearningTechniquesPage,
)
from cms.utils import (
    create_and_add_b2b_section,
    create_and_add_how_you_will_learn_section,
)

pytestmark = [pytest.mark.django_db]


def _create_learning_technique_common_child_page(platform=None):
    common_folder = CommonComponentIndexPageFactory.create()
    assert LearningTechniquesCommonPage.can_create_at(common_folder)
    return LearningTechniqueCommonPageFactory.create(
        platform=platform, parent=common_folder
    )


def _create_for_teams_common_child_page(platform=None):
    common_folder = CommonComponentIndexPageFactory.create()
    assert ForTeamsCommonPage.can_create_at(common_folder)
    return ForTeamsCommonPageFactory.create(platform=platform, parent=common_folder)


def _assert_common_page_creation(page, common_page, page_type, platform=None):
    assert page_type.can_create_at(page)

    platform_name = platform.name if platform else None
    if page_type is LearningTechniquesPage:
        create_and_add_how_you_will_learn_section(page, platform=platform_name)
    elif page_type is ForTeamsPage:
        create_and_add_b2b_section(page, platform=platform_name)

    # Invalidate cached property
    del page.child_pages_including_draft

    created_page = page.get_child_page_of_type_including_draft(page_type)
    assert created_page is not None
    assert created_page.title == common_page.title


@pytest.mark.parametrize(
    ("page_klass", "common_page_type"),
    [
        # LearningTechniquesCommonPage
        (ExternalCoursePageFactory, LearningTechniquesPage),
        (CoursePageFactory, LearningTechniquesPage),
        # ForTeamsCommonPage
        (ExternalCoursePageFactory, ForTeamsPage),
        (CoursePageFactory, ForTeamsPage),
    ],
)
def test_create_and_add_common_child_pages_with_platform(page_klass, common_page_type):
    platform = PlatformFactory.create()
    if common_page_type is LearningTechniquesPage:
        common_page = _create_learning_technique_common_child_page(platform)
    elif common_page_type is ForTeamsPage:
        common_page = _create_for_teams_common_child_page(platform)

    page = page_klass.create(course__platform=platform)

    _assert_common_page_creation(page, common_page, common_page_type, platform)


@pytest.mark.parametrize(
    ("page_klass", "common_page_type"),
    [
        # LearningTechniquesCommonPage
        (ExternalCoursePageFactory, LearningTechniquesPage),
        (CoursePageFactory, LearningTechniquesPage),
        # ForTeamsCommonPage
        (ExternalCoursePageFactory, ForTeamsPage),
        (CoursePageFactory, ForTeamsPage),
    ],
)
def test_create_and_add_common_child_pages_without_platform(
    page_klass, common_page_type
):
    if common_page_type is LearningTechniquesPage:
        common_page = _create_learning_technique_common_child_page()
    elif common_page_type is ForTeamsPage:
        common_page = _create_for_teams_common_child_page()

    page = page_klass.create()

    _assert_common_page_creation(page, common_page, common_page_type)


@pytest.mark.parametrize(
    ("page_klass", "common_page_type"),
    [
        # LearningTechniquesCommonPage
        (ExternalCoursePageFactory, LearningTechniquesPage),
        (CoursePageFactory, LearningTechniquesPage),
        # ForTeamsCommonPage
        (ExternalCoursePageFactory, ForTeamsPage),
        (CoursePageFactory, ForTeamsPage),
    ],
)
def test_create_and_add_common_child_pages_with_course_platform(
    page_klass, common_page_type
):
    if common_page_type is LearningTechniquesPage:
        common_page = _create_learning_technique_common_child_page()
    elif common_page_type is ForTeamsPage:
        common_page = _create_for_teams_common_child_page()

    page = page_klass.create(course__platform__name="something")

    _assert_common_page_creation(page, common_page, common_page_type)


@pytest.mark.parametrize(
    ("page_klass", "common_page_type"),
    [
        # LearningTechniquesCommonPage
        (ExternalCoursePageFactory, LearningTechniquesPage),
        (CoursePageFactory, LearningTechniquesPage),
        # ForTeamsCommonPage
        (ExternalCoursePageFactory, ForTeamsPage),
        (CoursePageFactory, ForTeamsPage),
    ],
)
def test_create_and_add_common_child_pages_with_different_platforms(
    page_klass, common_page_type
):
    course_platform = PlatformFactory.create(name="course platform")
    common_page_platform = PlatformFactory.create(name="common page platform")

    if common_page_type is LearningTechniquesPage:
        _create_learning_technique_common_child_page(common_page_platform)
    elif common_page_type is ForTeamsPage:
        _create_for_teams_common_child_page(common_page_platform)

    page = page_klass.create(course__platform=course_platform)

    create_and_add_how_you_will_learn_section(page, platform=course_platform.name)
    del page.child_pages_including_draft

    created_page = page.get_child_page_of_type_including_draft(common_page_type)
    assert created_page is None
