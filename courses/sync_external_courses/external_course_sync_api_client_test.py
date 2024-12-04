"""
Tests for external_course_sync_api_client
"""

import json
from datetime import timedelta

import pytest

from courses.sync_external_courses.external_course_sync_api_client import ExternalCourseSyncAPIClient
from mitxpro.test_utils import MockResponse
from mitxpro.utils import now_in_utc


@pytest.mark.parametrize(
    (
        "patch_request_path",
        "mock_response",
        "client_method",
        "args",
        "expected_api_url",
    ),
    [
        (
            "courses.sync_external_courses.external_course_sync_api_client.requests.get",
            MockResponse(
                {
                    "results": [
                        {
                            "id": 77,
                            "name": "Batch",
                        }
                    ]
                }
            ),
            "get_queries_list",
            [],
            "https://test-emeritus-api.io/api/queries?api_key=test_external_course_sync_api_key",
        ),
        (
            "courses.sync_external_courses.external_course_sync_api_client.requests.get",
            MockResponse({"job": {"status": 1}}),
            "get_job_status",
            [12],
            "https://test-emeritus-api.io/api/jobs/12?api_key=test_external_course_sync_api_key",
        ),
        (
            "courses.sync_external_courses.external_course_sync_api_client.requests.get",
            MockResponse({"query_result": {"data": {}}}),
            "get_query_result",
            [20],
            "https://test-emeritus-api.io/api/query_results/20?api_key=test_external_course_sync_api_key",
        ),
    ],
)
def test_external_course_sync_api_client_get_requests(  # noqa: PLR0913
    mocker,
    settings,
    patch_request_path,
    mock_response,
    client_method,
    args,
    expected_api_url,
):
    settings.EXTERNAL_COURSE_SYNC_API_KEY = "test_external_course_sync_api_key"
    settings.EXTERNAL_COURSE_SYNC_API_BASE_URL = "https://test-emeritus-api.io"
    settings.EXTERNAL_COURSE_SYNC_API_REQUEST_TIMEOUT = 60

    mock_get = mocker.patch(patch_request_path)
    mock_get.return_value = mock_response

    client = ExternalCourseSyncAPIClient()
    client_method_map = {
        "get_queries_list": client.get_queries_list,
        "get_job_status": client.get_job_status,
        "get_query_result": client.get_query_result,
    }
    client_method_map[client_method](*args)
    mock_get.assert_called_once_with(
        expected_api_url,
        timeout=60,
    )


def test_get_query_response(mocker, settings):
    """
    Tests that `ExternalCourseSyncAPIClient.get_query_response` makes the expected post request.
    """
    end_date = now_in_utc()
    start_date = end_date - timedelta(days=1)

    settings.EXTERNAL_COURSE_SYNC_API_KEY = "test_external_course_sync_api_key"
    settings.EXTERNAL_COURSE_SYNC_API_BASE_URL = "https://test-emeritus-api.io"

    mock_post = mocker.patch(
        "courses.sync_external_courses.external_course_sync_api_client.requests.post"
    )
    mock_post.return_value = MockResponse({"job": {"id": 1}})

    client = ExternalCourseSyncAPIClient()
    client.get_query_response(1, start_date, end_date)
    mock_post.assert_called_once_with(
        "https://test-emeritus-api.io/api/queries/1/results?api_key=test_external_course_sync_api_key",
        data=json.dumps(
            {
                "parameters": {
                    "date_range": {"start": f"{start_date}", "end": f"{end_date}"}
                }
            }
        ),
        timeout=60,
    )
