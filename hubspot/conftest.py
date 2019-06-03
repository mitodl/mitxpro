"""fixtures for hubspot tests"""
import pytest

error_response_json = [
    {
        "portalId": 5_890_463,
        "objectType": "CONTACT",
        "integratorObjectId": "16",
        "changeOccurredTimestamp": 1_558_727_887_000,
        "errorTimestamp": 1_558_727_887_000,
        "type": "UNKNOWNERROR",
        "details": 'Error performing[CREATE] CONTACT[16] for portal 5890463, error was [5890463] create/update by email failed - java.util.concurrent.CompletionException: com.hubspot.properties.exceptions.InvalidProperty: {"validationResults":[{"isValid":false,"message":"2019-05-13T12:05:53.602759Z was not a valid long.","error":"INVALIDLONG","name":"createdate"}],"status":"error","message":"Property values were not valid","correlationId":"fcde9e27-6e3b-4b3b-83c2-f6bd01289685","requestId":"8ede7b56-8269-4a5c-b2ea-a48a2dd9cd5d',
        "status": "OPEN",
    },
    {
        "portalId": 5_890_463,
        "objectType": "CONTACT",
        "integratorObjectId": "55",
        "changeOccurredTimestamp": 1_558_382_138_000,
        "errorTimestamp": 1_558_382_138_000,
        "type": "UNKNOWNERROR",
        "details": 'Error performing[CREATE] CONTACT[55] for portal 5890463, error was [5890463] create/update by email failed - java.util.concurrent.CompletionException: com.hubspot.properties.exceptions.InvalidProperty: {"validationResults":[{"isValid":false,"message":"2019-05-21T17:32:43.135139Z was not a valid long.","error":"INVALIDLONG","name":"createdate"}],"status":"error","message":"Property values were not valid","correlationId":"51274e2f-d839-4476-a077-eba7a38d3786","requestId":"9c1f2ded-78da-41a2-a607-568acfbd908f',
        "status": "OPEN",
    },
    {
        "portalId": 5_890_463,
        "objectType": "DEAL",
        "integratorObjectId": "116",
        "changeOccurredTimestamp": 1_558_727_887_000,
        "errorTimestamp": 1_508_727_887_000,
        "type": "UNKNOWNERROR",
        "details": 'Error performing[CREATE] DEAL[116] for portal 5890463, error was [5890463] create/update by email failed - java.util.concurrent.CompletionException: com.hubspot.properties.exceptions.InvalidProperty: {"validationResults":[{"isValid":false,"message":"2019-05-13T12:05:53.602759Z was not a valid long.","error":"INVALIDLONG","name":"createdate"}],"status":"error","message":"Property values were not valid","correlationId":"fcde9e27-6e3b-4b3b-83c2-f6bd01289685","requestId":"8ede7b56-8269-4a5c-b2ea-a48a2dd9cd5d',
        "status": "OPEN",
    },
    {
        "portalId": 5_890_463,
        "objectType": "DEAL",
        "integratorObjectId": "155",
        "changeOccurredTimestamp": 1_558_382_138_000,
        "errorTimestamp": 1_508_382_138_000,
        "type": "UNKNOWNERROR",
        "details": 'Error performing[CREATE] DEAL[155] for portal 5890463, error was [5890463] create/update by email failed - java.util.concurrent.CompletionException: com.hubspot.properties.exceptions.InvalidProperty: {"validationResults":[{"isValid":false,"message":"2019-05-21T17:32:43.135139Z was not a valid long.","error":"INVALIDLONG","name":"createdate"}],"status":"error","message":"Property values were not valid","correlationId":"51274e2f-d839-4476-a077-eba7a38d3786","requestId":"9c1f2ded-78da-41a2-a607-568acfbd908f',
        "status": "OPEN",
    },
]


@pytest.fixture
def mock_hubspot_errors(mocker):
    """Mock the get_sync_errors API call, assuming a limit of 2"""
    yield mocker.patch(
        "hubspot.api.paged_sync_errors",
        side_effect=[error_response_json[0:2], error_response_json[2:]],
    )
