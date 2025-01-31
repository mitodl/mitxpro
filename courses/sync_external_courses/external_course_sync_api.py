"""API for external course sync"""

import json
import logging
import re
import time
from datetime import timedelta
from decimal import Decimal
from enum import Enum
from pathlib import Path

from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models import Subquery
from wagtail.images.models import Image
from wagtail.models import Page

from cms.api import save_page_revision
from cms.models import (
    CertificatePage,
    CourseIndexPage,
    CourseOverviewPage,
    ExternalCoursePage,
    LearningOutcomesPage,
    WhoShouldEnrollPage,
)
from cms.wagtail_hooks import create_common_child_pages_for_external_courses
from courses.api import generate_course_readable_id
from courses.models import Course, CourseLanguage, CourseRun, CourseTopic, Platform
from courses.sync_external_courses.external_course_sync_api_client import (
    ExternalCourseSyncAPIClient,
)
from ecommerce.models import Product, ProductVersion
from mitxpro.utils import clean_url, now_in_utc, strip_datetime

log = logging.getLogger(__name__)

EMERITUS_PLATFORM_NAME = "Emeritus"
GLOBAL_ALUMNI_PLATFORM_NAME = "Global Alumni"


class ExternalCourseVendorBaseKeyMap:
    """
    Base class for course sync keys with common attributes.
    """

    date_format = "%Y-%m-%d"
    required_fields = [
        "course_title",
        "course_code",
        "course_run_code",
        "list_currency",
    ]
    who_should_enroll_page_heading = "WHO SHOULD ENROLL"
    learning_outcomes_page_heading = "WHAT YOU WILL LEARN"

    def __init__(self, platform_name, report_names):
        self.platform_name = platform_name
        self.report_names = report_names

    @property
    def course_page_subhead(self):
        return f"Delivered in collaboration with {self.platform_name}."

    @property
    def learning_outcomes_page_subhead(self):
        return (
            f"MIT xPRO is collaborating with online education provider {self.platform_name} to "
            "deliver this online course. By clicking LEARN MORE, you will be taken to "
            "a page where you can download the brochure and apply to the program via "
            f"{self.platform_name}."
        )


class EmeritusKeyMap(ExternalCourseVendorBaseKeyMap):
    """
    Emeritus course sync keys.
    """

    def __init__(self):
        super().__init__(platform_name=EMERITUS_PLATFORM_NAME, report_names=["Batch"])


class GlobalAlumniKeyMap(ExternalCourseVendorBaseKeyMap):
    """
    Global Alumni course sync keys.
    """

    def __init__(self):
        super().__init__(
            platform_name=GLOBAL_ALUMNI_PLATFORM_NAME, report_names=["GA - Batch"]
        )


EXTERNAL_COURSE_VENDOR_KEYMAPS = {
    EMERITUS_PLATFORM_NAME.lower(): EmeritusKeyMap,
    GLOBAL_ALUMNI_PLATFORM_NAME.lower(): GlobalAlumniKeyMap,
}


class ExternalCourseSyncAPIJobStatus(Enum):
    """
    Status of an External Course API Job.
    """

    READY = 3
    FAILED = 4
    CANCELLED = 5


class ExternalCourse:
    """
    External course object.

    Parses an External course JSON to Python object.
    """

    def __init__(self, external_course_json, keymap):
        program_name = external_course_json.get("program_name", None)
        self.course_title = program_name.strip() if program_name else None
        self.course_code = external_course_json.get("course_code")

        # External course code format is `<MXP | MO>-<COURSE_TAG>`, where course tag can contain `.`,
        # we will replace `.` with `_` to follow the internal readable id format.
        self.course_readable_id = generate_course_readable_id(
            self.course_code.split("-")[1].replace(".", "_")
        )

        self.course_run_code = external_course_json.get("course_run_code")
        self.course_run_tag = generate_external_course_run_tag(self.course_run_code)
        self.price = (
            float(external_course_json.get("list_price"))
            if external_course_json.get("list_price")
            else None
        )
        self.list_currency = external_course_json.get("list_currency")

        self.start_date = strip_datetime(
            external_course_json.get("start_date"), keymap.date_format
        )
        end_datetime = strip_datetime(
            external_course_json.get("end_date"), keymap.date_format
        )
        self.end_date = (
            end_datetime.replace(hour=23, minute=59) if end_datetime else None
        )
        # External Courses does not allow enrollments after start date.
        # We set the course run enrollment_end to the start date to
        # hide the course run from the course details page.
        self.enrollment_end = self.start_date

        self.marketing_url = clean_url(
            external_course_json.get("landing_page_url"), remove_query_params=True
        )
        total_weeks = int(external_course_json.get("total_weeks"))
        self.duration = f"{total_weeks} Weeks" if total_weeks != 0 else ""
        self.min_weeks = total_weeks
        self.max_weeks = total_weeks
        # If there is no language in the API we will default it to "English"
        self.language = external_course_json.get("language", "English").strip()

        # Description can be null in External Course API data, we cannot store `None` as description is Non-Nullable
        self.description = (
            external_course_json.get("description")
            if external_course_json.get("description")
            else ""
        )
        self.format = external_course_json.get("format")
        self.category = external_course_json.get("Category", None)
        self.image_name = external_course_json.get("image_name", None)
        self.CEUs = Decimal(str(external_course_json.get("ceu") or "0.0")) or None
        self.learning_outcomes_list = (
            parse_external_course_data_str(
                external_course_json.get("learning_outcomes")
            )
            if external_course_json.get("learning_outcomes")
            else []
        )
        self.who_should_enroll_list = (
            parse_external_course_data_str(external_course_json.get("program_for"))
            if external_course_json.get("program_for")
            else []
        )

    def validate_required_fields(self, keymap):
        """
        Validates the course data.
        Args:
            keymap(ExternalCourseVendorBaseKeyMap): An ExternalCourseVendorBaseKeyMap object
        """
        for field in keymap.required_fields:
            if not getattr(self, field, None):
                log.info(f"Missing required field {field}")  # noqa: G004
                return False
        return True

    def validate_list_currency(self):
        """
        Validates that the price is in USD.

        We only support `USD`. To support any other currency, we will have to manage the conversion to `USD`.
        """
        if self.list_currency != "USD":
            log.info(f"Invalid currency: {self.list_currency}.")  # noqa: G004
            return False
        return True

    def validate_end_date(self):
        """
        Validates that the course end date is in the future.
        """
        return self.end_date and now_in_utc() < self.end_date


def fetch_external_courses(keymap):
    """
    Fetches external courses data.
    Args:
        keymap(ExternalCourseVendorBaseKeyMap): An ExternalCourseVendorBaseKeyMap object

    Makes a request to get the list of available queries and then queries the required reports.
    """
    end_date = now_in_utc()
    start_date = end_date - timedelta(days=1)

    external_course_sync_api_client = ExternalCourseSyncAPIClient()
    queries = external_course_sync_api_client.get_queries_list()

    for query in queries:  # noqa: RET503
        # Check if query is in list of desired reports
        if query["name"] not in keymap.report_names:
            log.info(
                "Report: {} not specified for extract...skipping".format(query["name"])  # noqa: G001
            )
            continue

        log.info("Requesting data for {}...".format(query["name"]))  # noqa: G001
        query_response = external_course_sync_api_client.get_query_response(
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
                job_status = external_course_sync_api_client.get_job_status(job_id)
                if (
                    job_status["job"]["status"]
                    == ExternalCourseSyncAPIJobStatus.READY.value
                ):
                    # If true, the query_result is ready to be collected.
                    log.info("Job complete... requesting results...")
                    query_response = external_course_sync_api_client.get_query_result(
                        job_status["job"]["query_result_id"]
                    )
                    break
                elif job_status["job"]["status"] in [
                    ExternalCourseSyncAPIJobStatus.FAILED.value,
                    ExternalCourseSyncAPIJobStatus.CANCELLED.value,
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


def update_external_course_runs(external_courses, keymap):  # noqa: C901, PLR0915
    """
    Updates or creates the required course data i.e. Course, CourseRun,
    ExternalCoursePage, CourseTopic, WhoShouldEnrollPage, and LearningOutcomesPage

    Args:
        external_courses(list[dict]): A list of External Courses as a dict.
        keymap(ExternalCourseVendorBaseKeyMap): An ExternalCourseVendorBaseKeyMap object
    Returns:
        dict: Stats of all the objects created/updated.
    """
    platform, _ = Platform.objects.get_or_create(
        name__iexact=keymap.platform_name,
        defaults={"name": keymap.platform_name},
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
        "course_runs_deactivated": set(),
    }

    external_course_run_codes = [run["course_run_code"] for run in external_courses]
    deactivated_course_run_codes = deactivate_removed_course_runs(
        external_course_run_codes, platform.name.lower()
    )
    stats["course_runs_deactivated"] = deactivated_course_run_codes

    for external_course_json in external_courses:
        external_course = ExternalCourse(external_course_json, keymap)

        log.info(
            "Creating or updating course metadata for title: {}, course_code: {}, course_run_code: {}".format(  # noqa: G001, UP032
                external_course.course_title,
                external_course.course_code,
                external_course.course_run_code,
            )
        )
        if (
            not external_course.validate_required_fields(keymap)
            or not external_course.validate_list_currency()
        ):
            log.info(
                f"Skipping due to bad data... Course data: {json.dumps(external_course_json)}"  # noqa: G004
            )
            stats["course_runs_skipped"].add(external_course.course_run_code)
            continue

        if not external_course.validate_end_date():
            log.info(
                f"Course run is expired, Skipping... Course data: {json.dumps(external_course_json)}"  # noqa: G004
            )
            stats["course_runs_expired"].add(external_course.course_run_code)
            continue

        with transaction.atomic():
            course, course_created = Course.objects.get_or_create(
                external_course_id=external_course.course_code,
                platform=platform,
                is_external=True,
                defaults={
                    "title": external_course.course_title,
                    "readable_id": external_course.course_readable_id,
                    # All new courses are live by default, we will change the status manually
                    "live": True,
                },
            )

            if course_created:
                stats["courses_created"].add(external_course.course_code)
                log.info(
                    f"Created course, title: {external_course.course_title}, readable_id: {external_course.course_readable_id}"  # noqa: G004
                )
            else:
                stats["existing_courses"].add(external_course.course_code)
                log.info(
                    f"Course already exists, title: {external_course.course_title}, readable_id: {external_course.course_readable_id}"  # noqa: G004
                )

            log.info(
                f"Creating or Updating course run, title: {external_course.course_title}, course_run_code: {external_course.course_run_code}"  # noqa: G004
            )
            course_run, course_run_created, course_run_updated = (
                create_or_update_external_course_run(course, external_course)
            )

            if course_run_created:
                stats["course_runs_created"].add(course_run.external_course_run_id)
                log.info(
                    f"Created Course Run, title: {external_course.course_title}, external_course_run_id: {course_run.external_course_run_id}"  # noqa: G004
                )
            elif course_run_updated:
                stats["course_runs_updated"].add(course_run.external_course_run_id)
                log.info(
                    f"Updated Course Run, title: {external_course.course_title}, external_course_run_id: {course_run.external_course_run_id}"  # noqa: G004
                )

            log.info(
                f"Creating or Updating Product and Product Version, course run courseware_id: {course_run.external_course_run_id}, Price: {external_course.price}"  # noqa: G004
            )

            if external_course.price:
                product_created, product_version_created = (
                    create_or_update_product_and_product_version(
                        external_course, course_run
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
                        f"Created Product Version for course run: {course_run.courseware_id}, Price: {external_course.price}"  # noqa: G004
                    )
            else:
                log.info(
                    f"Price is Null for course run code: {external_course.course_run_code}"  # noqa: G004
                )
                stats["course_runs_without_prices"].add(external_course.course_run_code)

            log.info(
                f"Creating or Updating course page, title: {external_course.course_title}, course_code: {external_course.course_run_code}"  # noqa: G004
            )
            course_page, course_page_created, course_page_updated = (
                create_or_update_external_course_page(
                    course_index_page, course, external_course, keymap
                )
            )

            if course_page_created:
                stats["course_pages_created"].add(external_course.course_code)
                log.info(
                    f"Created external course page for course title: {external_course.course_title}"  # noqa: G004
                )
            elif course_page_updated:
                stats["course_pages_updated"].add(external_course.course_code)
                log.info(
                    f"Updated external course page for course title: {external_course.course_title}"  # noqa: G004
                )

            if external_course.category:
                topic = CourseTopic.objects.filter(
                    name__iexact=external_course.category
                ).first()
                if topic:
                    course_page.topics.add(topic)
                    course_page.save()
                    log.info(
                        f"Added topic {topic.name} for {external_course.course_title}"  # noqa: G004
                    )

            outcomes_page = course_page.get_child_page_of_type_including_draft(
                LearningOutcomesPage
            )
            if not outcomes_page and external_course.learning_outcomes_list:
                create_learning_outcomes_page(
                    course_page, external_course.learning_outcomes_list, keymap
                )
                log.info("Created LearningOutcomesPage.")

            who_should_enroll_page = course_page.get_child_page_of_type_including_draft(
                WhoShouldEnrollPage
            )
            if not who_should_enroll_page and external_course.who_should_enroll_list:
                create_who_should_enroll_in_page(
                    course_page, external_course.who_should_enroll_list, keymap
                )
                log.info("Created WhoShouldEnrollPage.")

            if external_course.CEUs:
                log.info(
                    f"Creating or Updating Certificate Page for title: {external_course.course_title}, course_code: {course.readable_id}, CEUs: {external_course.CEUs}"  # noqa: G004
                )
                _, is_certificatepage_created, is_certificatepage_updated = (
                    create_or_update_certificate_page(course_page, external_course)
                )

                if is_certificatepage_created:
                    log.info("Certificate Page Created")
                    stats["certificates_created"].add(course.readable_id)
                elif is_certificatepage_updated:
                    stats["certificates_updated"].add(course.readable_id)
                    log.info("Certificate Page Updated")

            overview_page = course_page.get_child_page_of_type_including_draft(
                CourseOverviewPage
            )
            if not overview_page and external_course.description:
                create_course_overview_page(course_page, external_course)
                log.info("Created CourseOverviewPage.")

            create_common_child_pages_for_external_courses(None, course_page)

    # As we get the API data for course runs, we can have duplicate course codes in course created and updated,
    # so, we are removing the courses created from the updated courses list.
    stats["existing_courses"] = stats["existing_courses"].difference(
        stats["courses_created"]
    )
    stats["course_pages_updated"] = stats["course_pages_updated"].difference(
        stats["course_pages_created"]
    )
    return stats


def create_or_update_product_and_product_version(external_course, course_run):
    """
    Creates or Updates Product and Product Version for the course run.

    Args:
        external_course(ExternalCourse): ExternalCourse object
        course_run(CourseRun): CourseRun object

    Returns:
        tuple: (product is created, product version is created)
    """
    product, product_created = Product.all_objects.get_or_create(
            content_type=ContentType.objects.get_for_model(CourseRun),
            object_id=course_run.id,
        )
    if not product_created and not product.is_active:
        product.is_active = True
        product.save()

    current_price = course_run.current_price
    if not current_price or current_price != external_course.price:    
        ProductVersion.objects.create(
            product=product,
            price=external_course.price,
            description=course_run.courseware_id,
        )
        return product_created, True
    return product_created, False


def generate_external_course_run_tag(course_run_code):
    """
    Returns the course run tag generated using the External Course run code.

    External course run codes follow a pattern `<MXP | MO>-<COURSE_CODE>-<RUN_TAG>`. This method returns the run tag.

    Args:
        course_run_code(str): External course code

    Returns:
        str: Course tag generated from the External Course Code
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


def create_or_update_external_course_page(  # noqa: C901
    course_index_page, course, external_course, keymap
):
    """
    Creates or updates external course page for External course.

    Args:
        course_index_page(CourseIndexPage): A course index page object.
        course(Course): A course object.
        external_course(ExternalCourse): A ExternalCourse object.

    Returns:
        tuple(ExternalCoursePage, is_created, is_updated): ExternalCoursePage object, is_created, is_updated
    """
    course_page = (
        ExternalCoursePage.objects.select_for_update().filter(course=course).first()
    )
    course_language, _ = CourseLanguage.objects.get_or_create(
        name__icontains=external_course.language
    )

    image = None
    if external_course.image_name:
        image = (
            Image.objects.filter(title=external_course.image_name)
            .order_by("-created_at")
            .first()
        )

        if not image:
            image_title = Path(external_course.image_name).stem
            image = (
                Image.objects.filter(title=image_title).order_by("-created_at").first()
            )

    is_created = is_updated = False
    if not course_page:
        course_page = ExternalCoursePage(
            course=course,
            title=external_course.course_title,
            external_marketing_url=external_course.marketing_url,
            subhead=keymap.course_page_subhead,
            duration=external_course.duration,
            min_weeks=external_course.min_weeks,
            max_weeks=external_course.max_weeks,
            format=external_course.format,
            description=external_course.description,
            background_image=image,
            thumbnail_image=image,
            language=course_language,
        )
        course_index_page.add_child(instance=course_page)
        course_page.save_revision().publish()
        is_created = True
    else:
        latest_revision = course_page.get_latest_revision_as_object()

        # Only update course page fields with API if they are empty in the latest revision.
        if not latest_revision.external_marketing_url and external_course.marketing_url:
            latest_revision.external_marketing_url = external_course.marketing_url
            is_updated = True

        if not latest_revision.duration and external_course.duration:
            latest_revision.duration = external_course.duration
            is_updated = True

        if not latest_revision.min_weeks and external_course.min_weeks:
            latest_revision.min_weeks = external_course.min_weeks
            is_updated = True

        if not latest_revision.max_weeks and external_course.max_weeks:
            latest_revision.max_weeks = external_course.max_weeks
            is_updated = True

        if not latest_revision.description and external_course.description:
            latest_revision.description = external_course.description
            is_updated = True

        if not latest_revision.background_image and image:
            latest_revision.background_image = image
            is_updated = True

        if not latest_revision.thumbnail_image and image:
            latest_revision.thumbnail_image = image
            is_updated = True

        # If the language is different from the course page language, update the language.
        if getattr(latest_revision, "language", None) != course_language:
            latest_revision.language = course_language
            is_updated = True

        if is_updated:
            save_page_revision(course_page, latest_revision)

    return course_page, is_created, is_updated


def create_or_update_external_course_run(course, external_course):
    """
    Creates or updates the external course run.

    Args:
        course (courses.Course): Course object
        external_course (ExternalCourse): ExternalCourse object

    Returns:
        tuple(CourseRun, is_created, is_updated): A tuple containing course run, is course run created, is course run updated
    """
    course_run_courseware_id = generate_external_course_run_courseware_id(
        external_course.course_run_tag, course.readable_id
    )
    course_run = (
        CourseRun.objects.select_for_update()
        .filter(external_course_run_id=external_course.course_run_code, course=course)
        .first()
    )
    is_created = is_updated = False

    if not course_run:
        course_run = CourseRun.objects.create(
            external_course_run_id=external_course.course_run_code,
            course=course,
            title=external_course.course_title,
            courseware_id=course_run_courseware_id,
            run_tag=external_course.course_run_tag,
            start_date=external_course.start_date,
            end_date=external_course.end_date,
            enrollment_end=external_course.enrollment_end,
            live=True,
        )
        is_created = True
    elif (
        (not course_run.start_date and external_course.start_date)
        or (
            course_run.start_date
            and external_course.start_date
            and course_run.start_date.date() != external_course.start_date.date()
        )
        or (not course_run.end_date and external_course.end_date)
        or (
            course_run.end_date
            and external_course.end_date
            and course_run.end_date.date() != external_course.end_date.date()
        )
        or (not course_run.enrollment_end and external_course.enrollment_end)
        or (
            course_run.enrollment_end
            and external_course.enrollment_end
            and course_run.enrollment_end.date()
            != external_course.enrollment_end.date()
        )
        or course_run.live is False
    ):
        course_run.start_date = external_course.start_date
        course_run.end_date = external_course.end_date
        course_run.enrollment_end = external_course.enrollment_end
        course_run.live = True
        course_run.save()
        is_updated = True

    return course_run, is_created, is_updated


def create_who_should_enroll_in_page(course_page, who_should_enroll_list, keymap):
    """
    Creates `WhoShouldEnrollPage` for external course.

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
        heading=keymap.who_should_enroll_page_heading,
        content=content,
    )
    course_page.add_child(instance=who_should_enroll_page)
    who_should_enroll_page.save()


def create_learning_outcomes_page(course_page, outcomes_list, keymap):
    """
    Creates `LearningOutcomesPage` for external course.

    Args:
        course_page(ExternalCoursePage): ExternalCoursePage object.
        outcomes_list(list): List of outcomes.
    """
    outcome_items = json.dumps(
        [{"type": "outcome", "value": outcome} for outcome in outcomes_list]
    )

    learning_outcome_page = LearningOutcomesPage(
        heading=keymap.learning_outcomes_page_heading,
        sub_heading=keymap.learning_outcomes_page_subhead,
        outcome_items=outcome_items,
    )
    course_page.add_child(instance=learning_outcome_page)
    learning_outcome_page.save()


def create_or_update_certificate_page(course_page, external_course):
    """
    Creates or Updates certificate page for a course page.

    Args:
        course_page(ExternalCoursePage): ExternalCoursePage object
        external_course(ExternalCourse): ExternalCourse object

    Returns:
        tuple: (CertificatePage, Is Page Created, Is Page Updated)
    """
    certificate_page = course_page.get_child_page_of_type_including_draft(
        CertificatePage
    )
    is_created = is_updated = False

    if not certificate_page:
        certificate_page = CertificatePage(
            product_name=f"Certificate for {external_course.course_title}",
            CEUs=external_course.CEUs,
            live=False,
        )
        course_page.add_child(instance=certificate_page)
        certificate_page.save_revision().publish()
        is_created = True
    else:
        latest_revision = certificate_page.get_latest_revision_as_object()

        if latest_revision.CEUs != external_course.CEUs:
            latest_revision.CEUs = external_course.CEUs
            is_updated = True

        if is_updated:
            save_page_revision(certificate_page, latest_revision)

    return certificate_page, is_created, is_updated


def parse_external_course_data_str(items_str):
    """
    Parses `WhoShouldEnrollPage` and `LearningOutcomesPage` items for the external API.

    Args:
        items_str(str): String containing a list of items separated by `\r\n`.

    Returns:
        list: List of items.
    """
    items_list = items_str.strip().split("\r\n")
    return [item.replace("●", "").strip() for item in items_list][1:]


def create_course_overview_page(
    course_page: ExternalCoursePage, external_course: ExternalCourse
):
    """
    Creates `CourseOverviewPage` for External course.

    Args:
        course_page(ExternalCoursePage): ExternalCoursePage object.
        external_course(ExternalCourse): ExternalCourse object
    """
    overview_page = CourseOverviewPage(overview=external_course.description)
    course_page.add_child(instance=overview_page)
    overview_page.save()


def deactivate_removed_course_runs(external_course_run_codes, platform_name):
    """
    Deactivate the course runs in future that are not returned by external course sync.

    Args:
        external_course_run_codes (list): List of external course run codes.
        platform_name (str): Name of the platform.
    """
    course_runs = CourseRun.objects.filter(
        course__platform__name__iexact=platform_name,
        start_date__gt=now_in_utc(),
        live=True,
    ).exclude(external_course_run_id__in=external_course_run_codes)
    course_runs.update(live=False)

    Product.objects.filter(object_id__in=Subquery(course_runs.values("id"))).update(
        is_active=False
    )

    log.info(
        f"Deactivated {course_runs.count()} course runs for platform {platform_name}."
    )
    return set(course_runs.values_list("external_course_run_id", flat=True))
