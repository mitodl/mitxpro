from cms.models import (
    ForTeamsExternalCoursePage,
    ForTeamsPage,
    LearningTechniquesExternalCoursePage,
    LearningTechniquesPage,
)


def create_how_you_will_learn_section(platform=None):
    learning_tech_page = LearningTechniquesExternalCoursePage.objects.all()
    if platform:
        learning_tech_page = learning_tech_page.filter(platform__name__iexact=platform)

    learning_tech_page = learning_tech_page.first()
    if not learning_tech_page:
        learning_tech_page = LearningTechniquesExternalCoursePage.objects.get(
            platform__isnull=True
        )

    return (
        LearningTechniquesPage(
            title=learning_tech_page.title,
            technique_items=learning_tech_page.technique_items,
        )
        if learning_tech_page
        else None
    )


def create_b2b_section(platform=None):
    b2b_page = ForTeamsExternalCoursePage.objects.all()
    if platform:
        b2b_page = b2b_page.filter(platform__name__iexact=platform)

    b2b_page = b2b_page.first()
    if not b2b_page:
        b2b_page = ForTeamsExternalCoursePage.objects.get(platform__isnull=True)

    return (
        ForTeamsPage(
            title=b2b_page.title,
            content=b2b_page.content,
            action_title=b2b_page.action_title,
            action_url=b2b_page.action_url,
            image=b2b_page.image,
        )
        if b2b_page
        else None
    )
