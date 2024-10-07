"""API for Emeritus course sync"""

import json
import logging
import re
import time
from datetime import timedelta
from enum import Enum
from pathlib import Path

from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from wagtail.images.models import Image
from wagtail.models import Page

from cms.models import (
    CertificatePage,
    CourseIndexPage,
    ExternalCoursePage,
    LearningOutcomesPage,
    WhoShouldEnrollPage,
)
from courses.api import generate_course_readable_id
from courses.models import Course, CourseRun, CourseTopic, Platform
from courses.sync_external_courses.emeritus_api_client import EmeritusAPIClient
from ecommerce.models import Product, ProductVersion
from mitxpro.utils import clean_url, now_in_utc, strip_datetime

log = logging.getLogger(__name__)


class EmeritusKeyMap(Enum):
    """
    Emeritus course sync keys.
    """

    REPORT_NAMES = ["Batch"]
    PLATFORM_NAME = "Emeritus"
    DATE_FORMAT = "%Y-%m-%d"
    COURSE_PAGE_SUBHEAD = "Delivered in collaboration with Emeritus."
    WHO_SHOULD_ENROLL_PAGE_HEADING = "WHO SHOULD ENROLL"
    LEARNING_OUTCOMES_PAGE_HEADING = "WHAT YOU WILL LEARN"
    LEARNING_OUTCOMES_PAGE_SUBHEAD = (
        "MIT xPRO is collaborating with online education provider Emeritus to "
        "deliver this online course. By clicking LEARN MORE, you will be taken to "
        "a page where you can download the brochure and apply to the program via Emeritus."
    )


class EmeritusJobStatus(Enum):
    """
    Status of an Emeritus Job.
    """

    READY = 3
    FAILED = 4
    CANCELLED = 5


class EmeritusCourse:
    """
    Emeritus course object.

    Parses an Emeritus course JSON to Python object.
    """

    def __init__(self, emeritus_course_json):
        self.course_title = emeritus_course_json.get("program_name", None)
        self.course_code = emeritus_course_json.get("course_code")

        # Emeritus course code format is `MO-<COURSE_TAG>`, where course tag can contain `.`,
        # we will replace `.` with `_` to follow the internal readable id format.
        self.course_readable_id = generate_course_readable_id(
            self.course_code.split("-")[1].replace(".", "_")
        )

        self.course_run_code = emeritus_course_json.get("course_run_code")
        self.course_run_tag = generate_emeritus_course_run_tag(self.course_run_code)
        self.price = (
            float(emeritus_course_json.get("list_price"))
            if emeritus_course_json.get("list_price")
            else None
        )
        self.list_currency = emeritus_course_json.get("list_currency")

        self.start_date = strip_datetime(
            emeritus_course_json.get("start_date"), EmeritusKeyMap.DATE_FORMAT.value
        )
        end_datetime = strip_datetime(
            emeritus_course_json.get("end_date"), EmeritusKeyMap.DATE_FORMAT.value
        )
        self.end_date = (
            end_datetime.replace(hour=23, minute=59) if end_datetime else None
        )
        # Emeritus does not allow enrollments after start date.
        # We set the course run enrollment_end to the start date to
        # hide the course run from the course details page.
        self.enrollment_end = self.start_date

        self.marketing_url = clean_url(
            emeritus_course_json.get("landing_page_url"), remove_query_params=True
        )
        total_weeks = int(emeritus_course_json.get("total_weeks"))
        self.duration = f"{total_weeks} Weeks" if total_weeks != 0 else ""

        # Description can be null in Emeritus API data, we cannot store `None` as description is Non-Nullable
        self.description = (
            emeritus_course_json.get("description")
            if emeritus_course_json.get("description")
            else ""
        )
        self.format = emeritus_course_json.get("format")
        self.category = emeritus_course_json.get("Category", None)
        self.image_name = emeritus_course_json.get("image_name", None)
        self.CEUs = str(emeritus_course_json.get("ceu") or "")
        self.learning_outcomes_list = (
            parse_emeritus_data_str(emeritus_course_json.get("learning_outcomes"))
            if emeritus_course_json.get("learning_outcomes")
            else []
        )
        self.who_should_enroll_list = (
            parse_emeritus_data_str(emeritus_course_json.get("program_for"))
            if emeritus_course_json.get("program_for")
            else []
        )

    def validate_required_fields(self):
        """
        Validates the course data.
        """
        required_fields = [
            "course_title",
            "course_code",
            "course_run_code",
            "list_currency",
        ]
        for field in required_fields:
            if not getattr(self, field, None):
                log.info(f"Missing required field {field}")  # noqa: G004
                return False
        return True

    def valid_list_currency(self):
        """
        Validates that the price is in USD.
        """
        # We only support `USD`. To support any other currency, we will have to manage the conversion to `USD`.
        if self.price and self.list_currency != "USD":
            log.info(f"Invalid currency: {self.list_currency}.")  # noqa: G004
            return False
        return True

    def valid_end_date(self):
        """
        Validates that the course end date is in the future.
        """
        return now_in_utc() < self.end_date


def fetch_emeritus_courses():
    """
    Fetches Emeritus courses data.

    Makes a request to get the list of available queries and then queries the required reports.
    """
    end_date = now_in_utc()
    start_date = end_date - timedelta(days=1)

    emeritus_api_client = EmeritusAPIClient()
    queries = emeritus_api_client.get_queries_list()

    for query in queries:  # noqa: RET503
        # Check if query is in list of desired reports
        if query["name"] not in EmeritusKeyMap.REPORT_NAMES.value:
            log.info(
                "Report: {} not specified for extract...skipping".format(query["name"])  # noqa: G001
            )
            continue

        log.info("Requesting data for {}...".format(query["name"]))  # noqa: G001
        query_response = emeritus_api_client.get_query_response(
            query["id"], start_date, end_date
        )
        if "job" in query_response:
            # If a job is returned, we will poll until status = 3 (Success)
            # Status values 1 and 2 correspond to in-progress,
            # while 4 and 5 correspond to Failed, and Canceled, respectively.
            job_id = query_response["job"]["id"]
            log.info(
                f"Job id: {job_id} found... waiting for completion..."  # noqa: G004
            )
            while True:
                job_status = emeritus_api_client.get_job_status(job_id)
                if job_status["job"]["status"] == EmeritusJobStatus.READY.value:
                    # If true, the query_result is ready to be collected.
                    log.info("Job complete... requesting results...")
                    query_response = emeritus_api_client.get_query_result(
                        job_status["job"]["query_result_id"]
                    )
                    break
                elif job_status["job"]["status"] in [
                    EmeritusJobStatus.FAILED.value,
                    EmeritusJobStatus.CANCELLED.value,
                ]:
                    log.error("Job failed!")
                    break
                else:
                    # Continue waiting until complete.
                    log.info("Job not yet complete... sleeping for 2 seconds...")
                    time.sleep(2)

        if "query_result" in query_response:
            # Check that query_result is in the data payload.
            # Return result as json
            return dict(query_response["query_result"]["data"]).get("rows", [])
        log.error("Something unexpected happened!")


def update_emeritus_course_runs(emeritus_courses):  # noqa: C901, PLR0915
    """
    Updates or creates the required course data i.e. Course, CourseRun,
    ExternalCoursePage, CourseTopic, WhoShouldEnrollPage, and LearningOutcomesPage

    Args:
        emeritus_courses(list[dict]): A list of Emeritus Courses as a dict.

    Returns:
        dict: Stats of all the objects created/updated.
    """
    platform, _ = Platform.objects.get_or_create(
        name__iexact=EmeritusKeyMap.PLATFORM_NAME.value,
        defaults={"name": EmeritusKeyMap.PLATFORM_NAME.value},
    )
    course_index_page = Page.objects.get(id=CourseIndexPage.objects.first().id).specific
    stats = {
        "courses_created": set(),
        "existing_courses": set(),
        "course_runs_created": set(),
        "course_runs_updated": set(),
        "course_pages_created": set(),
        "course_pages_updated": set(),
        "course_runs_skipped": set(),
        "course_runs_expired": set(),
        "products_created": set(),
        "product_versions_created": set(),
        "course_runs_without_prices": set(),
        "certificates_created": set(),
        "certificates_updated": set(),
    }

    for emeritus_course_json in emeritus_courses:
        emeritus_course = EmeritusCourse(emeritus_course_json)

        log.info(
            "Creating or updating course metadata for title: {}, course_code: {}, course_run_code: {}".format(  # noqa: G001, UP032
                emeritus_course.course_title,
                emeritus_course.course_code,
                emeritus_course.course_run_code,
            )
        )
        if (
            not emeritus_course.validate_required_fields()
            or not emeritus_course.valid_list_currency()
        ):
            log.info(
                f"Skipping due to bad data... Course data: {json.dumps(emeritus_course_json)}"  # noqa: G004
            )
            stats["course_runs_skipped"].add(emeritus_course.course_run_code)
            continue

        if not emeritus_course.valid_end_date():
            log.info(
                f"Course run is expired, Skipping... Course data: {json.dumps(emeritus_course_json)}"  # noqa: G004
            )
            stats["course_runs_expired"].add(emeritus_course.course_run_code)
            continue

        with transaction.atomic():
            course, course_created = Course.objects.get_or_create(
                external_course_id=emeritus_course.course_code,
                platform=platform,
                is_external=True,
                defaults={
                    "title": emeritus_course.course_title,
                    "readable_id": emeritus_course.course_readable_id,
                    # All new courses are live by default, we will change the status manually
                    "live": True,
                },
            )

            if course_created:
                stats["courses_created"].add(emeritus_course.course_code)
                log.info(
                    f"Created course, title: {emeritus_course.course_title}, readable_id: {emeritus_course.course_readable_id}"  # noqa: G004
                )
            else:
                stats["existing_courses"].add(emeritus_course.course_code)
                log.info(
                    f"Course already exists, title: {emeritus_course.course_title}, readable_id: {emeritus_course.course_readable_id}"  # noqa: G004
                )

            log.info(
                f"Creating or Updating course run, title: {emeritus_course.course_title}, course_run_code: {emeritus_course.course_run_code}"  # noqa: G004
            )
            course_run, course_run_created, course_run_updated = (
                create_or_update_emeritus_course_run(course, emeritus_course)
            )

            if course_run_created:
                stats["course_runs_created"].add(course_run.external_course_run_id)
                log.info(
                    f"Created Course Run, title: {emeritus_course.course_title}, external_course_run_id: {course_run.external_course_run_id}"  # noqa: G004
                )
            elif course_run_updated:
                stats["course_runs_updated"].add(course_run.external_course_run_id)
                log.info(
                    f"Updated Course Run, title: {emeritus_course.course_title}, external_course_run_id: {course_run.external_course_run_id}"  # noqa: G004
                )

            log.info(
                f"Creating or Updating Product and Product Version, course run courseware_id: {course_run.external_course_run_id}, Price: {emeritus_course.price}"  # noqa: G004
            )

            if emeritus_course.price:
                product_created, product_version_created = (
                    create_or_update_product_and_product_version(
                        emeritus_course, course_run
                    )
                )
                if product_created:
                    stats["products_created"].add(course_run.external_course_run_id)
                    log.info(
                        f"Created Product for course run: {course_run.courseware_id}"  # noqa: G004
                    )

                if product_version_created:
                    stats["product_versions_created"].add(
                        course_run.external_course_run_id
                    )
                    log.info(
                        f"Created Product Version for course run: {course_run.courseware_id}, Price: {emeritus_course.price}"  # noqa: G004
                    )
            else:
                log.info(
                    f"Price is Null for course run code: {emeritus_course.course_run_code}"  # noqa: G004
                )
                stats["course_runs_without_prices"].add(emeritus_course.course_run_code)

            log.info(
                f"Creating or Updating course page, title: {emeritus_course.course_title}, course_code: {emeritus_course.course_run_code}"  # noqa: G004
            )
            course_page, course_page_created, course_page_updated = (
                create_or_update_emeritus_course_page(
                    course_index_page, course, emeritus_course
                )
            )

            if course_page_created:
                stats["course_pages_created"].add(emeritus_course.course_code)
                log.info(
                    f"Created external course page for course title: {emeritus_course.course_title}"  # noqa: G004
                )
            elif course_page_updated:
                stats["course_pages_updated"].add(emeritus_course.course_code)
                log.info(
                    f"Updated external course page for course title: {emeritus_course.course_title}"  # noqa: G004
                )

            if emeritus_course.category:
                topic = CourseTopic.objects.filter(
                    name__iexact=emeritus_course.category
                ).first()
                if topic:
                    course_page.topics.add(topic)
                    course_page.save()
                    log.info(
                        f"Added topic {topic.name} for {emeritus_course.course_title}"  # noqa: G004
                    )

            outcomes_page = course_page.get_child_page_of_type_including_draft(
                LearningOutcomesPage
            )
            if not outcomes_page and emeritus_course.learning_outcomes_list:
                create_learning_outcomes_page(
                    course_page, emeritus_course.learning_outcomes_list
                )
                log.info("Created LearningOutcomesPage.")

            who_should_enroll_page = course_page.get_child_page_of_type_including_draft(
                WhoShouldEnrollPage
            )
            if not who_should_enroll_page and emeritus_course.who_should_enroll_list:
                create_who_should_enroll_in_page(
                    course_page, emeritus_course.who_should_enroll_list
                )
                log.info("Created WhoShouldEnrollPage.")

            if emeritus_course.CEUs:
                log.info(
                    f"Creating or Updating Certificate Page for title: {emeritus_course.course_title}, course_code: {course.readable_id}, CEUs: {emeritus_course.CEUs}"  # noqa: G004
                )
                _, is_certificatepage_created, is_certificatepage_updated = (
                    create_or_update_certificate_page(course_page, emeritus_course)
                )

                if is_certificatepage_created:
                    log.info("Certificate Page Created")
                    stats["certificates_created"].add(course.readable_id)
                elif is_certificatepage_updated:
                    stats["certificates_updated"].add(course.readable_id)
                    log.info("Certificate Page Updated")

    # As we get the API data for course runs, we can have duplicate course codes in course created and updated,
    # so, we are removing the courses created from the updated courses list.
    stats["existing_courses"] = stats["existing_courses"].difference(
        stats["courses_created"]
    )
    stats["course_pages_updated"] = stats["course_pages_updated"].difference(
        stats["course_pages_created"]
    )
    return stats


def create_or_update_product_and_product_version(emeritus_course, course_run):
    """
    Creates or Updates Product and Product Version for the course run.

    Args:
        emeritus_course(EmeritusCourse): EmeritusCourse object
        course_run(CourseRun): CourseRun object

    Returns:
        tuple: (product is created, product version is created)
    """
    current_price = course_run.current_price
    if not current_price or current_price != emeritus_course.price:
        product, product_created = Product.objects.get_or_create(
            content_type=ContentType.objects.get_for_model(CourseRun),
            object_id=course_run.id,
        )
        ProductVersion.objects.create(
            product=product,
            price=emeritus_course.price,
            description=course_run.courseware_id,
        )
        return product_created, True
    return False, False


def generate_emeritus_course_run_tag(course_run_code):
    """
    Returns the course run tag generated using the Emeritus Course run code.

    Emeritus course run codes follow a pattern `MO-<COURSE_CODE>-<RUN_TAG>`. This method returns the run tag.

    Args:
        course_run_code(str): Emeritus course code

    Returns:
        str: Course tag generated from the Emeritus Course Code
    """
    run_tag = re.search(r"[0-9]{2}-[0-9]{2}#[0-9]+$", course_run_code).group(0)
    return run_tag.replace("#", "-")


def generate_external_course_run_courseware_id(course_run_tag, course_readable_id):
    """
    Returns course run courseware id using the course readable id and course run tag.

    Args:
        course_run_tag(str): CourseRun tag for the course.
        course_readable_id(str): Course readable_id

    Returns:
        str: Course run courseware_id
    """
    return f"{course_readable_id}+{course_run_tag}"


def create_or_update_emeritus_course_page(course_index_page, course, emeritus_course):
    """
    Creates or updates external course page for Emeritus course.

    Args:
        course_index_page(CourseIndexPage): A course index page object.
        course(Course): A course object.
        emeritus_course(EmeritusCourse): A EmeritusCourse object.

    Returns:
        tuple(ExternalCoursePage, is_created, is_updated): ExternalCoursePage object, is_created, is_updated
    """
    course_page = (
        ExternalCoursePage.objects.select_for_update().filter(course=course).first()
    )

    image = None
    if emeritus_course.image_name:
        image = (
            Image.objects.filter(title=emeritus_course.image_name)
            .order_by("-created_at")
            .first()
        )

        if not image:
            image_title = Path(emeritus_course.image_name).stem
            image = (
                Image.objects.filter(title=image_title).order_by("-created_at").first()
            )

    is_created = is_updated = False
    if not course_page:
        course_page = ExternalCoursePage(
            course=course,
            title=emeritus_course.course_title,
            external_marketing_url=emeritus_course.marketing_url,
            subhead=EmeritusKeyMap.COURSE_PAGE_SUBHEAD.value,
            duration=emeritus_course.duration,
            format=emeritus_course.format,
            description=emeritus_course.description,
            background_image=image,
            thumbnail_image=image,
        )
        course_index_page.add_child(instance=course_page)
        course_page.save_revision().publish()
        is_created = True
    else:
        latest_revision = course_page.get_latest_revision_as_object()

        # Only update course page fields with API if they are empty in the latest revision.
        if not latest_revision.external_marketing_url and emeritus_course.marketing_url:
            latest_revision.external_marketing_url = emeritus_course.marketing_url
            is_updated = True

        if not latest_revision.duration and emeritus_course.duration:
            latest_revision.duration = emeritus_course.duration
            is_updated = True

        if not latest_revision.description and emeritus_course.description:
            latest_revision.description = emeritus_course.description
            is_updated = True

        if not latest_revision.background_image and image:
            latest_revision.background_image = image
            is_updated = True

        if not latest_revision.thumbnail_image and image:
            latest_revision.thumbnail_image = image
            is_updated = True

        if is_updated:
            save_page_revision(course_page, latest_revision)

    return course_page, is_created, is_updated


def create_or_update_emeritus_course_run(course, emeritus_course):
    """
    Creates or updates the external emeritus course run.

    Args:
        course (courses.Course): Course object
        emeritus_course (EmeritusCourse): EmeritusCourse object

    Returns:
        tuple(CourseRun, is_created, is_updated): A tuple containing course run, is course run created, is course run updated
    """
    course_run_courseware_id = generate_external_course_run_courseware_id(
        emeritus_course.course_run_tag, course.readable_id
    )
    course_run = (
        CourseRun.objects.select_for_update()
        .filter(external_course_run_id=emeritus_course.course_run_code, course=course)
        .first()
    )
    is_created = is_updated = False

    if not course_run:
        course_run = CourseRun.objects.create(
            external_course_run_id=emeritus_course.course_run_code,
            course=course,
            title=emeritus_course.course_title,
            courseware_id=course_run_courseware_id,
            run_tag=emeritus_course.course_run_tag,
            start_date=emeritus_course.start_date,
            end_date=emeritus_course.end_date,
            enrollment_end=emeritus_course.enrollment_end,
            live=True,
        )
        is_created = True
    elif (
        (not course_run.start_date and emeritus_course.start_date)
        or (
            course_run.start_date
            and emeritus_course.start_date
            and course_run.start_date.date() != emeritus_course.start_date.date()
        )
        or (not course_run.end_date and emeritus_course.end_date)
        or (
            course_run.end_date
            and emeritus_course.end_date
            and course_run.end_date.date() != emeritus_course.end_date.date()
        )
        or (not course_run.enrollment_end and emeritus_course.enrollment_end)
        or (
            course_run.enrollment_end
            and emeritus_course.enrollment_end
            and course_run.enrollment_end.date()
            != emeritus_course.enrollment_end.date()
        )
    ):
        course_run.start_date = emeritus_course.start_date
        course_run.end_date = emeritus_course.end_date
        course_run.enrollment_end = emeritus_course.enrollment_end
        course_run.save()
        is_updated = True

    return course_run, is_created, is_updated


def create_who_should_enroll_in_page(course_page, who_should_enroll_list):
    """
    Creates `WhoShouldEnrollPage` for Emeritus course.

    Args:
        course_page(ExternalCoursePage): ExternalCoursePage object.
        who_should_enroll_list(list): List of who should enroll items.
    """
    content = json.dumps(
        [
            {"type": "item", "value": who_should_enroll_item}
            for who_should_enroll_item in who_should_enroll_list
        ]
    )

    who_should_enroll_page = WhoShouldEnrollPage(
        heading=EmeritusKeyMap.WHO_SHOULD_ENROLL_PAGE_HEADING.value,
        content=content,
    )
    course_page.add_child(instance=who_should_enroll_page)
    who_should_enroll_page.save()


def create_learning_outcomes_page(course_page, outcomes_list):
    """
    Creates `LearningOutcomesPage` for Emeritus course.

    Args:
        course_page(ExternalCoursePage): ExternalCoursePage object.
        outcomes_list(list): List of outcomes.
    """
    outcome_items = json.dumps(
        [{"type": "outcome", "value": outcome} for outcome in outcomes_list]
    )

    learning_outcome_page = LearningOutcomesPage(
        heading=EmeritusKeyMap.LEARNING_OUTCOMES_PAGE_HEADING.value,
        sub_heading=EmeritusKeyMap.LEARNING_OUTCOMES_PAGE_SUBHEAD.value,
        outcome_items=outcome_items,
    )
    course_page.add_child(instance=learning_outcome_page)
    learning_outcome_page.save()


def create_or_update_certificate_page(course_page, emeritus_course):
    """
    Creates or Updates certificate page for a course page.

    Args:
        course_page(ExternalCoursePage): ExternalCoursePage object
        emeritus_course(EmeritusCourse): EmeritusCourse object

    Returns:
        tuple: (CertificatePage, Is Page Created, Is Page Updated)
    """
    certificate_page = course_page.get_child_page_of_type_including_draft(
        CertificatePage
    )
    is_created = is_updated = False

    if not certificate_page:
        certificate_page = CertificatePage(
            product_name=f"Certificate for {emeritus_course.course_title}",
            CEUs=emeritus_course.CEUs,
            live=False,
        )
        course_page.add_child(instance=certificate_page)
        certificate_page.save_revision().publish()
        is_created = True
    else:
        latest_revision = certificate_page.get_latest_revision_as_object()

        if latest_revision.CEUs != emeritus_course.CEUs:
            latest_revision.CEUs = emeritus_course.CEUs
            is_updated = True

        if is_updated:
            save_page_revision(certificate_page, latest_revision)

    return certificate_page, is_created, is_updated


def parse_emeritus_data_str(items_str):
    """
    Parses `WhoShouldEnrollPage` and `LearningOutcomesPage` items for the Emeritus API.

    Args:
        items_str(str): String containing a list of items separated by `\r\n`.

    Returns:
        list: List of items.
    """
    items_list = items_str.strip().split("\r\n")
    return [item.replace("●", "").strip() for item in items_list][1:]


def save_page_revision(page, updated_revision):
    """
    Saves the page revision and publishes it if page has no draft changes.

    Args:
        page(Page): A page object.
        updated_revision(Page): Updated Page object using the `latest_revision_as_object`
    """
    is_draft = page.has_unpublished_changes
    revision = updated_revision.save_revision(user=None, log_action=True)
    if not is_draft:
        revision.publish()
