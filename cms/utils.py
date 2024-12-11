from django.db import models

from cms.models import (
    ForTeamsCommonPage,
    ForTeamsPage,
    LearningTechniquesCommonPage,
    LearningTechniquesPage,
)


def create_and_add_how_you_will_learn_section(page, platform=None):
    """
    Creates and adds a LearningTechniquesPage section to the given page.

    Args:
        page: The parent page where the LearningTechniquesPage section will be added.
        platform (str, optional): The name of the platform to filter the learning
            techniques content. Defaults to None.

    Returns:
        None if the section already exists or no matching content is found. Otherwise,
        adds a `LearningTechniquesPage` with the relevant content as a child of the given page.
    """
    icongrid_page = page.get_child_page_of_type_including_draft(LearningTechniquesPage)
    if icongrid_page:
        return

    learning_tech_page = (
        LearningTechniquesCommonPage.objects.filter(
            models.Q(platform__name__iexact=platform)
            | models.Q(platform__name__isnull=True),
            live=True,
        )
        .order_by("platform__name")
        .first()
    )
    if not learning_tech_page:
        return

    tech_page = LearningTechniquesPage(
        title=learning_tech_page.title,
        technique_items=learning_tech_page.technique_items,
    )
    page.add_child(instance=tech_page)


def create_and_add_b2b_section(page, platform=None):
    """
    Creates and adds a "For Teams" (B2B) section to the given page.

    Args:
        page: The parent page where the "For Teams" section will be added.
        platform (str, optional): The name of the platform to filter the B2B content. Defaults to None.

    Returns:
        None if the section already exists or no matching content is found. Otherwise,
        adds a `ForTeamsPage` with the relevant content as a child of the given page.
    """
    b2b_page = page.get_child_page_of_type_including_draft(ForTeamsPage)
    if b2b_page:
        return

    b2b_page = (
        ForTeamsCommonPage.objects.filter(
            models.Q(platform__name__iexact=platform)
            | models.Q(platform__name__isnull=True),
            live=True,
        )
        .order_by("platform__name")
        .first()
    )
    if not b2b_page:
        return

    for_teams_page = ForTeamsPage(
        title=b2b_page.title,
        content=b2b_page.content,
        action_title=b2b_page.action_title,
        action_url=b2b_page.action_url,
        image=b2b_page.image,
    )
    page.add_child(instance=for_teams_page)
