import json
from datetime import timedelta

import requests
from django.conf import settings

from mitxpro.utils import now_in_utc


class EmeritusAPIClient:
    """
    API client for Emeritus
    """

    def __init__(self):
        self.api_key = settings.EMERITUS_API_KEY
        self.base_url = settings.EMERITUS_API_BASE_URL
        self.request_timeout = settings.EMERITUS_API_REQUEST_TIMEOUT

    def get_queries_list(self):
        """
        Get a list of available queries
        """
        queries = requests.get(
            f"{self.base_url}/api/queries?api_key={self.api_key}",
            timeout=self.request_timeout,
        )
        queries.raise_for_status()
        return queries.json()["result"]

    def get_query_response(self, query_id):
        """
        Make a post request for the query found.
        This will return either:
          a) A query_result if one is cached for the parameters set, or
          b) A Job object.
        """
        end_date = now_in_utc()
        start_date = end_date - timedelta(days=1)

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
