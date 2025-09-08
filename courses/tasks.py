"""
Tasks for the courses app
"""

import logging
from datetime import timedelta

from django.conf import settings
from django.db.models import Q
from requests.exceptions import HTTPError

from courses.models import CourseRun, CourseRunCertificate, Platform
from courses.sync_external_courses.external_course_sync_api import (
    EXTERNAL_COURSE_VENDOR_KEYMAPS,
    fetch_external_courses,
    update_external_course_runs,
)
from courses.utils import (
    ensure_course_run_grade,
    process_course_run_grade_certificate,
    sync_course_runs,
)
from courseware.api import get_edx_grades_with_users
from ecommerce.mail_api import send_external_data_sync_email
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
            - timedelta(hours=settings.CERTIFICATE_CREATION_DELAY_IN_HOURS),
            course__is_external=False,
        )
        .exclude(
            id__in=CourseRunCertificate.objects.values_list("course_run__id", flat=True)
        )
    )

    for run in course_runs:
        if not run.has_certificate_page:
            log.exception(
                "Course run %s has no certificate page. Skipping grades sync and certificate generation.",
                run,
            )
            continue

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
        except StopIteration:
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


@app.task
def task_sync_external_course_runs():
    """Task to sync external course runs"""
    platforms = Platform.objects.filter(enable_sync=True)
    for platform in platforms:
        keymap = EXTERNAL_COURSE_VENDOR_KEYMAPS.get(platform.name.lower())
        if not keymap:
            log.exception(
                "The platform '%s' does not have a sync API configured. Please disable the 'enable_sync' setting for this platform.",
                platform.name,
            )
            continue
        try:
            keymap = keymap()
            external_course_runs = fetch_external_courses(keymap)
            stats_collector = update_external_course_runs(external_course_runs, keymap)
            email_stats = stats_collector.get_email_stats()
            send_external_data_sync_email(
                vendor_name=platform.name.lower(),
                stats=email_stats,
            )
        except Exception:
            log.exception("Some error occurred")
