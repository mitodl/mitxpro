import json
import logging
import re
import time
from datetime import datetime, timedelta, timezone

import requests
from django.conf import settings
from wagtail.models import Page

from cms.models import (
    CourseIndexPage,
    ExternalCoursePage,
    LearningOutcomesPage,
    WhoShouldEnrollPage,
)
from courses.api import generate_course_readable_id
from courses.constants import (
    EMERITUS_COURSE_PAGE_SUBHEAD,
    EMERITUS_DATE_FORMAT,
    EMERITUS_LEARNING_OUTCOMES_PAGE_HEADING,
    EMERITUS_LEARNING_OUTCOMES_PAGE_SUBHEAD,
    EMERITUS_PLATFORM_NAME,
    EMERITUS_REPORT_NAMES,
    EMERITUS_WHO_SHOULD_ENROLL_PAGE_HEADING,
)
from courses.models import Course, CourseRun, CourseTopic, Platform
from courses.sync_external_courses.utils import EmeritusJobStatus
from mitxpro.utils import clean_url, now_in_utc

log = logging.getLogger(__name__)


def fetch_emeritus_course_runs():
    """
    Fetches Emeritus course runs.

    Makes a request to get the list of available queries and then queries the required reports.
    """
    api_base_url = settings.EMERITUS_API_BASE_URL
    api_key = settings.EMERITUS_API_KEY

    end_date = now_in_utc()
    start_date = end_date - timedelta(days=1)

    # Get a list of available queries
    queries = requests.get(
        f"{api_base_url}/api/queries?api_key={api_key}",
        timeout=settings.EMERITUS_API_REQUEST_TIMEOUT,
    )
    queries.raise_for_status()

    for report in queries.json()["results"]:  # noqa: RET503
        # Check if query is in list of desired reports
        if report["name"] not in EMERITUS_REPORT_NAMES:
            log.info(
                "Report: {} not specified for extract...skipping".format(report["name"])  # noqa: G001
            )
            continue

        log.info("Requesting data for {}...".format(report["name"]))  # noqa: G001

        # Make a post request for the query found.
        # This will return either:
        #   a) A query_result if one is cached for the parameters set, or
        #   b) A Job object.
        data = requests.post(
            f"{api_base_url}/api/queries/{report['id']}/results?api_key={api_key}",
            data=json.dumps(
                {
                    "parameters": {
                        "date_range": {"start": f"{start_date}", "end": f"{end_date}"}
                    }
                }
            ),
            timeout=settings.EMERITUS_API_REQUEST_TIMEOUT,
        )

        data.raise_for_status()
        data = data.json()
        if "job" in data:
            # If a job is returned, we will poll until status = 3 (Success)
            # Status values 1 and 2 correspond to in-progress,
            # while 4 and 5 correspond to Failed, and Canceled, respectively.
            job_id = data["job"]["id"]
            log.info(f"Job id: {job_id} found... waiting for completion...")  # noqa: G004
            while True:
                # Get the status of the job-id returned by the initial request.
                job_status = requests.get(
                    f"{api_base_url}/api/jobs/{job_id}?api_key={api_key}",
                    timeout=settings.EMERITUS_API_REQUEST_TIMEOUT,
                )
                job_status.raise_for_status()
                job_status = job_status.json()

                if job_status["job"]["status"] == EmeritusJobStatus.READY:
                    # If true, the query_result is ready to be collected.
                    log.info("Job complete... requesting results...")
                    query_resp = requests.get(
                        f"{api_base_url}/api/query_results/{job_status['job']['query_result_id']}?api_key={api_key}",
                        timeout=settings.EMERITUS_API_REQUEST_TIMEOUT,
                    )
                    query_resp.raise_for_status()
                    data = query_resp.json()
                    break
                elif job_status["job"]["status"] in [
                    EmeritusJobStatus.FAILED,
                    EmeritusJobStatus.CANCELLED,
                ]:
                    log.error("Job failed!")
                    break
                else:
                    # Continue waiting until complete.
                    log.info("Job not yet complete... sleeping for 2 seconds...")
                    time.sleep(2)

        if "query_result" in data:
            # Check that query_result is in the data payload.
            # Return result as json
            return dict(data["query_result"]["data"]).get("rows", [])
        log.error("Something unexpected happened!")


def update_emeritus_course_runs(emeritus_course_runs):
    """
    Updates or creates the required course data i.e. Course, CourseRun,
    ExternalCoursePage, CourseTopic, WhoShouldEnrollPage, and LearningOutcomesPage
    """
    platform = Platform.objects.get(name__iexact=EMERITUS_PLATFORM_NAME)
    course_index_page = Page.objects.get(id=CourseIndexPage.objects.first().id).specific
    for emeritus_course_run in emeritus_course_runs:
        course_title = emeritus_course_run.get("program_name")
        course_code = emeritus_course_run.get("course_code")
        course_run_code = emeritus_course_run.get("course_run_code")

        if not (course_title and course_code and course_run_code):
            log.info(
                f"Missing required course data. Skipping... Course data: {json.dumps(emeritus_course_run)}"  # noqa: G004
            )
            continue

        course_readable_id = generate_course_readable_id(course_code.split("-")[1])
        course, course_created = Course.objects.get_or_create(
            external_course_id=course_code,
            platform=platform,
            is_external=True,
            defaults={
                "title": course_title,
                "readable_id": course_readable_id,
                "live": True,
            },
        )
        log_msg = "Created course," if course_created else "Course already exists,"
        log.info(f"{log_msg} title: {course_title}, readable_id: {course_readable_id}")  # noqa: G004

        create_or_update_emeritus_course_run(course, emeritus_course_run)
        try:
            course_page = create_or_update_emeritus_course_page(
                course_index_page, course, emeritus_course_run
            )
        except Exception:
            log.exception(
                f"Could not create Course Page for {json.dumps(emeritus_course_run)}"  # noqa: G004
            )
            continue

        if emeritus_course_run.get("Category"):
            topic, _ = CourseTopic.objects.get_or_create(
                name=emeritus_course_run.get("Category")
            )
            course_page.topics.add(topic)
            course_page.save()

        if not course_page.outcomes and emeritus_course_run.get("learning_outcomes"):
            create_learning_outcomes_page(
                course_page, emeritus_course_run.get("learning_outcomes")
            )

        if not course_page.who_should_enroll and emeritus_course_run.get("program_for"):
            create_who_should_enroll_in_page(
                course_page, emeritus_course_run.get("program_for")
            )


def generate_emeritus_course_run_tag(course_run_code):
    """
    Returns the course tag generated using the Emeritus Course run code.

    Emeritus course run code follow a pattern `MO-<COURSE_CODE>-<RUN_TAG>`. This method returns the run tag.
    """
    return re.search(r"[0-9]{2}-[0-9]{2}#[0-9]+$", course_run_code).group(0)


def generate_external_course_run_courseware_id(course_run_tag, course_readable_id):
    """
    Returns course run courseware id using the course readable id and course run tag.
    """
    return f"{course_readable_id}+{course_run_tag}"


def create_or_update_emeritus_course_page(
    course_index_page, course, emeritus_course_run
):
    """
    Creates or updates external course page for Emeritus course run.
    """
    course_page = getattr(course, "externalcoursepage", None)
    marketing_url = clean_url(
        emeritus_course_run.get("landing_page_url"), remove_query_params=True
    )
    total_weeks = emeritus_course_run.get("total_weeks")
    duration = f"{total_weeks} Weeks" if total_weeks and total_weeks != 0 else ""
    description = (
        emeritus_course_run.get("description")
        if emeritus_course_run.get("description")
        else ""
    )

    if not course_page:
        course_page = ExternalCoursePage(
            course=course,
            title=emeritus_course_run["program_name"],
            external_marketing_url=marketing_url,
            subhead=EMERITUS_COURSE_PAGE_SUBHEAD,
            duration=duration,
            format=emeritus_course_run.get("format"),
            description=description,
        )
        course_index_page.add_child(instance=course_page)
        course_page.save()
    else:
        # Only update course page fields with API if they are empty.
        if not course_page.external_marketing_url and marketing_url:
            course_page.external_marketing_url = marketing_url
        if not course_page.duration and duration:
            course_page.duration = duration
        if not course_page.description and description:
            course_page.description = description
        course_page.save()

    return course_page


def create_or_update_emeritus_course_run(course, emeritus_course_run):
    """
    Creates or updates the external emeritus course run.
    """
    title = emeritus_course_run["program_name"]
    start_date_str = emeritus_course_run.get("start_date", None)
    end_date_str = emeritus_course_run.get("end_date", None)
    start_date = (
        datetime.strptime(start_date_str, EMERITUS_DATE_FORMAT).astimezone(timezone.utc)
        if start_date_str
        else None
    )
    end_date = (
        datetime.strptime(end_date_str, EMERITUS_DATE_FORMAT)
        .astimezone(timezone.utc)
        .replace(hour=23, minute=59)
        if end_date_str
        else None
    )

    course_run_code = emeritus_course_run.get("course_run_code")
    course_run_tag = generate_emeritus_course_run_tag(course_run_code)
    course_run_courseware_id = generate_external_course_run_courseware_id(
        course_run_tag, course.readable_id
    )
    course_run, created = CourseRun.objects.get_or_create(
        external_course_run_id=course_run_code,
        course=course,
        defaults={
            "title": title,
            "courseware_id": course_run_courseware_id,
            "run_tag": course_run_tag,
            "start_date": start_date,
            "end_date": end_date,
            "live": True,
        },
    )
    if created:
        log.info(
            f"Created Course Run, title: {title}, external_course_run_id: {course_run_code}"  # noqa: G004
        )
    elif (
        course_run.start_date.date() != start_date.date()
        or course_run.end_date.date() != end_date.date()
    ):
        course_run.start_date = start_date
        course_run.end_date = end_date
        course_run.save()
        log.info(
            f"Updated Course Run, title: {title}, external_course_run_id: {course_run_code}"  # noqa: G004
        )


def create_who_should_enroll_in_page(course_page, who_should_enroll_string):
    """
    Creates `WhoShouldEnrollPage` for Emeritus course.
    """
    who_should_enroll_list = parse_program_for_and_outcomes(who_should_enroll_string)
    content = json.dumps(
        [
            {"type": "item", "value": who_should_enroll_item}
            for who_should_enroll_item in who_should_enroll_list
        ]
    )

    who_should_enroll_page = WhoShouldEnrollPage(
        heading=EMERITUS_WHO_SHOULD_ENROLL_PAGE_HEADING,
        content=content,
    )
    course_page.add_child(instance=who_should_enroll_page)
    who_should_enroll_page.save()


def create_learning_outcomes_page(course_page, outcomes_string):
    """
    Creates `LearningOutcomesPage` for Emeritus course.
    """
    learning_outcomes = parse_program_for_and_outcomes(outcomes_string)
    outcome_items = json.dumps(
        [{"type": "outcome", "value": outcome} for outcome in learning_outcomes]
    )

    learning_outcome_page = LearningOutcomesPage(
        heading=EMERITUS_LEARNING_OUTCOMES_PAGE_HEADING,
        sub_heading=EMERITUS_LEARNING_OUTCOMES_PAGE_SUBHEAD,
        outcome_items=outcome_items,
    )
    course_page.add_child(instance=learning_outcome_page)
    learning_outcome_page.save()


def parse_program_for_and_outcomes(items_str):
    """
    Parses `WhoShouldEnrollPage` and `LearningOutcomesPage` items for the Emeritus API.
    """
    items_list = items_str.strip().split("\r\n")
    return [item.replace("●", "").strip() for item in items_list][1:]
