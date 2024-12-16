"""Tests for utility functions in cms/utils.py"""

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
    """
    Create a LearningTechniquesCommonPage and return a LearningTechniqueCommonPage
    """
    common_component_index = CommonComponentIndexPageFactory.create()
    assert LearningTechniquesCommonPage.can_create_at(common_component_index)
    return LearningTechniqueCommonPageFactory.create(
        platform=platform, parent=common_component_index
    )


def _create_for_teams_common_child_page(platform=None):
    """
    Create a ForTeamsCommonPage and return a ForTeamsCommonPage
    """
    common_component_index = CommonComponentIndexPageFactory.create()
    assert ForTeamsCommonPage.can_create_at(common_component_index)
    return ForTeamsCommonPageFactory.create(
        platform=platform, parent=common_component_index
    )


def _assert_common_page_creation(
    parent_page, common_child_page, page_type, platform=None
):
    """
    Assert that a common page was created and added to the given page
    """
    assert page_type.can_create_at(parent_page)

    platform_name = platform.name if platform else None
    if page_type is LearningTechniquesPage:
        create_and_add_how_you_will_learn_section(parent_page, platform=platform_name)
    elif page_type is ForTeamsPage:
        create_and_add_b2b_section(parent_page, platform=platform_name)

    # Invalidate cached property
    del parent_page.child_pages_including_draft

    created_page = parent_page.get_child_page_of_type_including_draft(page_type)
    assert created_page is not None
    assert created_page.title == common_child_page.title


@pytest.mark.parametrize(
    "parent_page_klass",
    [ExternalCoursePageFactory, CoursePageFactory],
)
@pytest.mark.parametrize(
    "common_page_type",
    [LearningTechniquesPage, ForTeamsPage],
)
@pytest.mark.parametrize(
    "platform_name",
    ["platform1", None],
)
def test_create_and_add_common_child_pages(
    parent_page_klass, common_page_type, platform_name
):
    """
    Test that a common page is created and added to the given page
    """
    platform = PlatformFactory.create(name=platform_name) if platform_name else None
    if common_page_type is LearningTechniquesPage:
        common_page = _create_learning_technique_common_child_page(platform)
    elif common_page_type is ForTeamsPage:
        common_page = _create_for_teams_common_child_page(platform)

    if platform_name:
        parent_page = parent_page_klass.create(course__platform=platform)
    else:
        parent_page = parent_page_klass.create()

    _assert_common_page_creation(parent_page, common_page, common_page_type, platform)


@pytest.mark.parametrize(
    "parent_page_klass",
    [ExternalCoursePageFactory, CoursePageFactory],
)
@pytest.mark.parametrize(
    "common_page_type",
    [LearningTechniquesPage, ForTeamsPage],
)
def test_create_and_add_common_child_pages_with_course_platform(
    parent_page_klass, common_page_type
):
    """
    Test that a common page is created and added to the given page if the platform is the same
    """
    if common_page_type is LearningTechniquesPage:
        common_page = _create_learning_technique_common_child_page()
    elif common_page_type is ForTeamsPage:
        common_page = _create_for_teams_common_child_page()

    parent_page = parent_page_klass.create(course__platform__name="something")

    _assert_common_page_creation(parent_page, common_page, common_page_type)


@pytest.mark.parametrize(
    "parent_page_klass",
    [ExternalCoursePageFactory, CoursePageFactory],
)
@pytest.mark.parametrize(
    "common_page_type",
    [LearningTechniquesPage, ForTeamsPage],
)
def test_create_and_add_common_child_pages_with_different_platforms(
    parent_page_klass, common_page_type
):
    """
    Test that a common page is not created and added to the given page if the platform is different
    """
    course_platform = PlatformFactory.create(name="course platform")
    common_page_platform = PlatformFactory.create(name="common page platform")

    if common_page_type is LearningTechniquesPage:
        _create_learning_technique_common_child_page(common_page_platform)
    elif common_page_type is ForTeamsPage:
        _create_for_teams_common_child_page(common_page_platform)

    parent_page = parent_page_klass.create(course__platform=course_platform)

    create_and_add_how_you_will_learn_section(
        parent_page, platform=course_platform.name
    )
    del parent_page.child_pages_including_draft

    created_page = parent_page.get_child_page_of_type_including_draft(common_page_type)
    assert created_page is None
