from pathlib import Path

from django.core.files import File
from wagtail.images.models import Image

from cms.constants import B2B_SECTION, HOW_YOU_WILL_LEARN_SECTION


def create_how_you_will_learn_section():
    from cms.models import LearningTechniquesPage

    section_content = HOW_YOU_WILL_LEARN_SECTION.copy()
    for technique in section_content["technique_items"]:
        image_title = technique["value"]["heading"]
        with Path(technique["value"]["image"]).open("rb") as img:
            img_file = File(img)
            image, _ = Image.objects.get_or_create(
                title=image_title, defaults={"file": img_file}
            )
            technique["value"]["image"] = image.id

    return LearningTechniquesPage(**section_content)


def create_b2b_section():
    from cms.models import ForTeamsPage

    section_content = B2B_SECTION.copy()
    with Path(section_content["image"]).open("rb") as img:
        img_file = File(img)
        image, _ = Image.objects.get_or_create(
            title=section_content["title"], defaults={"file": img_file}
        )
        section_content["image"] = image

    return ForTeamsPage(**section_content)
