import json
import logging
import re
import time
from datetime import datetime, timedelta

import requests
from django.conf import settings
from wagtail.models import Page

from cms.models import (
    CourseIndexPage,
    ExternalCoursePage,
    LearningOutcomesPage,
    WhoShouldEnrollPage,
)
from courses.constants import EMERITUS_REPORT_NAMES, EMERITUS_DATE_FORMAT, EMERITUS_PLATFORM_NAME
from courses.models import Course, CourseRun, CourseTopic, Platform

log = logging.getLogger(__name__)


def fetch_emeritus_course_runs():
    """
    Fetches Emeritus course runs.

    Makes a request to get the list of available queries and then queries the required reports.
    """
    api_base_url = settings.EMERITUS_API_BASE_URL
    api_key = settings.EMERITUS_API_KEY

    end_date = datetime.now()
    start_date = end_date - timedelta(days=1)

    # Get a list of available queries
    queries = requests.get(f"{api_base_url}/api/queries?api_key={api_key}", timeout=60)
    queries.raise_for_status()

    for report in queries.json()["results"]:
        # Check if query is in list of desired reports
        if report["name"] not in EMERITUS_REPORT_NAMES:
            # If not, continue.
            log.info(
                "Report: {} not specified for extract...skipping".format(report["name"])
            )
            continue

        log.info("Requesting data for {}...".format(report["name"]))

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
        )

        data.raise_for_status()
        data = data.json()
        if "job" in data.keys():
            # If a job is returned, we will poll until status = 3 (Success)
            # Status values 1 and 2 correspond to in-progress,
            # while 4 and 5 correspond to Failed, and Canceled, respectively.
            job_id = data["job"]["id"]
            log.info(f"Job id: {job_id} found... waiting for completion...")
            while True:
                # Get the status of the job-id returned by the initial request.
                job_status = requests.get(
                    f"{api_base_url}/api/jobs/{job_id}?api_key={api_key}"
                )
                job_status.raise_for_status()
                job_status = job_status.json()

                if job_status["job"]["status"] == 3:
                    # If true, the query_result is ready to be collected.
                    log.info("Job complete... requesting results...")
                    query_resp = requests.get(
                        f"{api_base_url}/api/query_results/{job_status['job']['query_result_id']}?api_key={api_key}"
                    )
                    query_resp.raise_for_status()
                    data = query_resp.json()
                    break
                elif job_status["job"]["status"] in [4, 5]:
                    # Error
                    log.error("Job failed!")
                    break
                else:
                    # Continue waiting until complete.
                    log.info("Job not yet complete... sleeping for 2 seconds...")
                    time.sleep(2)

        if "query_result" in data.keys():
            # Check that query_result is in the data payload.
            # Return result as json
            return dict(data["query_result"]["data"]).get("rows", [])
        log.error("Something unexpected happened!")


def update_emeritus_course_runs(emeritus_course_runs):
    """
    Updates or creates the required course data i.e. Course, CourseRun,
    ExternalCoursePage, CourseTopic, WhoShouldEnrollPage, and LearningOutcomesPage
    """
    platform, _ = Platform.objects.get_or_create(name=EMERITUS_PLATFORM_NAME)
    for emeritus_course_run in emeritus_course_runs:
        course_title = emeritus_course_run.get("program_name")
        course_code = emeritus_course_run.get("course_code")
        course_run_code = emeritus_course_run.get("course_run_code")
        if not (course_title and course_code and course_run_code):
            continue

        course = Course.objects.filter(
            external_course_id=course_code,
            platform=platform,
            is_external=True,
        ).first()
        course_readable_id = generate_course_readable_id(course_code)
        if not course:
            log.info(
                f"No course found for title: {course_title}, external_course_id: {course_code}. Creating a new one..."
            )

            course = Course.objects.create(
                title=course_title,
                readable_id=course_readable_id,
                external_course_id=course_code,
                platform=platform,
                live=True,
                is_external=True,
            )

        create_or_update_emeritus_course_run(course, course_title, course_readable_id, emeritus_course_run)
        course_page = create_or_update_external_course_page(course, course_title, emeritus_course_run)

        if emeritus_course_run.get("Category"):
            topic, _ = CourseTopic.objects.get_or_create(
                name=emeritus_course_run.get("Category")
            )
            course_page.topics.add(topic)

        if emeritus_course_run.get("learning_outcomes"):
            create_learning_outcomes_page(
                course_page, emeritus_course_run.get("learning_outcomes")
            )

        if emeritus_course_run.get("program_for"):
            create_who_should_enroll_in_page(
                course_page, emeritus_course_run.get("program_for")
            )


def generate_course_readable_id(external_course_code):
    """
    Generates course readable ID using the Emeritus Course code.
    """
    if not external_course_code:
        return ""

    external_course_tag = external_course_code.split("-")[1]
    return f"course-v1:xPRO+{external_course_tag}"


def generate_external_course_run_tag(course_run_code):
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


def create_or_update_external_course_page(course, course_title, emeritus_course_run):
    """
    Creates or updates external course page for Emeritus course page.
    """
    course_page = getattr(course, "externalcoursepage", None)
    if not course_page:
        course_page = ExternalCoursePage(
            course=course,
            title=course_title,
            external_marketing_url=emeritus_course_run.get("landing_page_url", ""),
            subhead="Delivered in collaboration with Emeritus.",
            duration=f"{emeritus_course_run.get('total_weeks')} Weeks",
            format=emeritus_course_run.get("format"),
            description=emeritus_course_run.get("description"),
        )
        course_index_page = Page.objects.get(
            id=CourseIndexPage.objects.first().id
        ).specific
        course_index_page.add_child(instance=course_page)
        course_page.save()
    else:
        pass

    return course_page


def create_or_update_emeritus_course_run(course, course_title, course_readable_id, emeritus_course_run):
    """
    Creates or updates the external emeritus course run.
    """
    start_date_str = emeritus_course_run.get("start_date", None)
    end_date_str = emeritus_course_run.get("end_date", None)
    start_date = (
        datetime.strptime(start_date_str, EMERITUS_DATE_FORMAT)
        if start_date_str
        else None
    )
    end_date = (
        datetime.strptime(end_date_str, EMERITUS_DATE_FORMAT)
        if end_date_str
        else None
    )

    course_run_code = emeritus_course_run.get("course_run_code")
    course_run = course.courseruns.filter(
        external_course_run_id=course_run_code
    ).first()
    if not course_run:
        log.info(
            f"Course run not found for external_course_run_id: {course_run_code}"
        )
        course_run_tag = generate_external_course_run_tag(course_run_code)
        course_run_courseware_id = generate_external_course_run_courseware_id(
            course_run_tag, course_readable_id
        )
        CourseRun.objects.create(
            course=course,
            title=course_title,
            courseware_id=course_run_courseware_id,
            run_tag=course_run_tag,
            external_course_run_id=course_run_code,
            start_date=start_date,
            end_date=end_date,
            live=True,
        )
    elif course_run.start_date != start_date or course_run.end_date != end_date:
        course_run.start_date = start_date
        course_run.end_date = end_date
        course_run.save()


def create_who_should_enroll_in_page(course_page, who_should_enroll_string):
    """
    Creates `WhoShouldEnrollPage` for Emeritus course.
    """
    who_should_enroll_list = who_should_enroll_string.strip().split("\r\n")
    who_should_enroll_list = [
        item.replace("●", "").strip() for item in who_should_enroll_list
    ][1:]
    who_should_enroll_page = WhoShouldEnrollPage(
        heading="WHO SHOULD ENROLL",
        content=json.dumps(
            [
                {"type": "item", "value": who_should_enroll_item}
                for who_should_enroll_item in who_should_enroll_list
            ]
        ),
    )
    course_page.add_child(who_should_enroll_page)
    who_should_enroll_page.save()


def create_learning_outcomes_page(course_page, outcomes_string):
    """
    Creates `LearningOutcomesPage` for Emeritus course.
    """
    learning_outcomes = outcomes_string.strip().split("\r\n")
    learning_outcomes = [
        outcome.replace("●", "").strip() for outcome in learning_outcomes
    ][1:]
    learning_outcome_page = LearningOutcomesPage(
        heading="WHAT YOU WILL LEARN",
        sub_heading="MIT xPRO is collaborating with online education provider Emeritus to deliver "
        "this online course. By clicking LEARN MORE, you will be taken to a page where "
        "you can download the brochure and apply to the program via Emeritus.",
        outcome_items=json.dumps(
            [{"type": "outcome", "value": outcome} for outcome in learning_outcomes]
        ),
    )
    course_page.add_child(instance=learning_outcome_page)
    learning_outcome_page.save()
