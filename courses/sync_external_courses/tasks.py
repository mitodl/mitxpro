import datetime
import json
import logging
import time

import requests
from django.conf import settings

from mitxpro.celery import app

LOG = logging.getLogger(__name__)

REPORT_NAMES = ["Batch"]


@app.task
def task_sync_emeritus_courses(n_days=1):
    """Task to sync courses for Emeritus"""
    api_base_url = settings.EMERITUS_API_BASE_URL
    api_key = settings.EMERITUS_API_KEY
    LOG.info(f"Starting api extract for {n_days}...")
    # Both reports have a last-modified timestamp field.
    # Use this to limit the results to only relevant records.
    last_date = datetime.datetime.now()
    first_date = last_date - datetime.timedelta(n_days)

    # Get a list of available queries
    queries = requests.get(f"{api_base_url}/api/queries?api_key={api_key}", timeout=60)
    queries.raise_for_status()

    for report in queries.json()["results"]:
        # Check if query is in list of desired reports
        if report["name"] not in REPORT_NAMES:
            # If not, continue.
            LOG.info(
                "Report: {} not specified for extract...skipping".format(report["name"])
            )
            continue

        LOG.info("Requesting data for {}...".format(report["name"]))

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
            LOG.info(f"Job id: {job_id} found...waiting for completion...")
            while True:
                # Get the status of the job-id returned by the initial request.
                job_status = requests.get(
                    f"{api_base_url}/api/jobs/{job_id}?api_key={api_key}"
                )
                job_status.raise_for_status()
                job_status = job_status.json()

                if job_status["job"]["status"] == 3:
                    # If true, the query_result is ready to be collected.
                    LOG.info("Job complete...requesting results...")
                    query_resp = requests.get(
                        f"{api_base_url}/api/query_results/{job_status['job']['query_result_id']}?api_key={api_key}"
                    )
                    query_resp.raise_for_status()
                    data = query_resp.json()
                    break
                elif job_status["job"]["status"] in [4, 5]:
                    # Error
                    LOG.error("Job failed!")
                    break
                else:
                    # Continue waiting until complete.
                    LOG.info("Job not yet complete... sleeping for 2 seconds...")
                    time.sleep(2)

        if "query_result" in data.keys():
            # Check that query_reesult is in the data payload.
            # Write result as json to the specified directory, using
            # the report title as the filename.
            results = dict(data["query_result"]["data"])
            LOG.info("Data written successfully!")
        else:
            LOG.error("Something unexpected happened!")
