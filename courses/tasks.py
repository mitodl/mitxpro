"""
Tasks for the courses app
"""

import json
import time
import logging
from datetime import datetime, timedelta
import requests

from django.conf import settings
from django.db.models import Q
from requests.exceptions import HTTPError

from courses.constants import EMERITUS_REPORT_NAMES
from courses.models import CourseRun, CourseRunCertificate
from courses.utils import (
    ensure_course_run_grade,
    process_course_run_grade_certificate,
    sync_course_runs,
)
from courseware.api import get_edx_grades_with_users
from mitxpro.celery import app
from mitxpro.utils import now_in_utc

log = logging.getLogger(__name__)


@app.task
def generate_course_certificates():
    """
    Task to generate certificates for courses.
    """
    now = now_in_utc()
    course_runs = (
        CourseRun.objects.live()
        .filter(
            end_date__lt=now
            - timedelta(hours=settings.CERTIFICATE_CREATION_DELAY_IN_HOURS)
        )
        .exclude(
            id__in=CourseRunCertificate.objects.values_list("course_run__id", flat=True)
        )
    )

    for run in course_runs:
        edx_grade_user_iter = exception_logging_generator(
            get_edx_grades_with_users(run)
        )
        created_grades_count, updated_grades_count, generated_certificates_count = (
            0,
            0,
            0,
        )
        for edx_grade, user in edx_grade_user_iter:
            course_run_grade, created, updated = ensure_course_run_grade(
                user=user, course_run=run, edx_grade=edx_grade, should_update=True
            )

            if created:
                created_grades_count += 1
            elif updated:
                updated_grades_count += 1

            _, created, deleted = process_course_run_grade_certificate(
                course_run_grade=course_run_grade
            )

            if deleted:
                log.warning(
                    "Certificate deleted for user %s and course_run %s", user, run
                )
            elif created:
                generated_certificates_count += 1

        log.info(
            "Finished processing course run %s: created grades for %d users, "
            "updated grades for %d users, generated certificates for %d users",
            run,
            created_grades_count,
            updated_grades_count,
            generated_certificates_count,
        )


def exception_logging_generator(generator):
    """Returns a new generator that logs exceptions from the given generator and continues with iteration"""
    while True:
        try:
            yield next(generator)
        except StopIteration:  # noqa: PERF203
            return
        except HTTPError as exc:
            log.exception("EdX API error for fetching user grades %s:", exc)  # noqa: TRY401
        except Exception as exp:
            log.exception("Error fetching user grades from edX %s:", exp)  # noqa: TRY401


@app.task
def sync_courseruns_data():
    """
    Task to sync titles and dates for course runs from edX. (Only internal courses)
    """
    now = now_in_utc()
    runs = list(
        CourseRun.objects.live().filter(
            Q(expiration_date__isnull=True) | Q(expiration_date__gt=now),
            course__is_external=False,
        )
    )

    # `sync_course_runs` logs internally so no need to capture/output the returned values
    sync_course_runs(runs)


# @app.task
def task_sync_emeritus_courses():
    """Task to sync courses for Emeritus"""
    data = fetch_emeritus_course_data()
    update_external_courses(data)

def update_external_courses(data):
    for course_run in data["rows"]:
        pass


def fetch_emeritus_course_data(n_days=1):
    """Fetch Emeritus course data"""
    api_base_url = settings.EMERITUS_API_BASE_URL
    api_key = settings.EMERITUS_API_KEY
    log.info(f"Starting api extract for {n_days}...")
    # Both reports have a last-modified timestamp field.
    # Use this to limit the results to only relevant records.
    last_date = datetime.now()
    first_date = last_date - timedelta(n_days)

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
                        "date_range": {"start": f"{first_date}", "end": f"{last_date}"}
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
            log.info(f"Job id: {job_id} found...waiting for completion...")
            while True:
                # Get the status of the job-id returned by the initial request.
                job_status = requests.get(
                    f"{api_base_url}/api/jobs/{job_id}?api_key={api_key}"
                )
                job_status.raise_for_status()
                job_status = job_status.json()

                if job_status["job"]["status"] == 3:
                    # If true, the query_result is ready to be collected.
                    log.info("Job complete...requesting results...")
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
            # Check that query_reesult is in the data payload.
            # Write result as json to the specified directory, using
            # the report title as the filename.
            results = dict(data["query_result"]["data"])
            return results
        else:
            log.error("Something unexpected happened!")

