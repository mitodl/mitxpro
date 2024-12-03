"""
API client for Emeritus
"""

import json

import requests
from django.conf import settings


class ExternalCourseSyncAPIClient:
    """
    API client for Emeritus
    """

    def __init__(self):
        self.api_key = settings.EXTERNAL_COURSE_SYNC_API_KEY
        self.base_url = settings.EXTERNAL_COURSE_SYNC_API_BASE_URL
        self.request_timeout = settings.EXTERNAL_COURSE_SYNC_API_REQUEST_TIMEOUT

    def get_queries_list(self):
        """
        Get a list of available queries
        """
        queries = requests.get(
            f"{self.base_url}/api/queries?api_key={self.api_key}",
            timeout=self.request_timeout,
        )
        queries.raise_for_status()
        return queries.json()["results"]

    def get_query_response(self, query_id, start_date, end_date):
        """
        Make a post request for the query.

        This will return either:
          a) A query_result if one is cached for the parameters set, or
          b) A Job object.
        """
        query_response = requests.post(
            f"{self.base_url}/api/queries/{query_id}/results?api_key={self.api_key}",
            data=json.dumps(
                {
                    "parameters": {
                        "date_range": {"start": f"{start_date}", "end": f"{end_date}"}
                    }
                }
            ),
            timeout=self.request_timeout,
        )
        query_response.raise_for_status()
        return query_response.json()

    def get_job_status(self, job_id):
        """
        Get the status of the job
        """
        job_status = requests.get(
            f"{self.base_url}/api/jobs/{job_id}?api_key={self.api_key}",
            timeout=self.request_timeout,
        )
        job_status.raise_for_status()
        return job_status.json()

    def get_query_result(self, query_result_id):
        """
        Get the query result
        """
        query_result = requests.get(
            f"{self.base_url}/api/query_results/{query_result_id}?api_key={self.api_key}",
            timeout=self.request_timeout,
        )
        query_result.raise_for_status()
        return query_result.json()
