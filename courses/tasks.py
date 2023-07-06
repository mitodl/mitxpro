"""
Tasks for the courses app
"""
import logging

from mitxpro.celery import app


log = logging.getLogger(__name__)


@app.task
def generate_course_certificates():
    """
    Task to generate certificates for courses.
    """
    from courses.api import generate_course_run_certificates

    generate_course_run_certificates()


@app.task
def sync_courseruns_data():
    """
    Task to sync course runs data
    """
    from courses.api import sync_course_runs_data

    sync_course_runs_data()
