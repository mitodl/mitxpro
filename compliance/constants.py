"""Compliance constants"""

# computed result states
RESULT_SUCCESS = "SUCCESS"
RESULT_MANUALLY_APPROVED = "MANUALLY_APPROVED"
RESULT_DENIED = "DENIED"
RESULT_TEMPORARY_FAILURE = "TEMPORARY_FAILURE"
RESULT_UNKNOWN = "UNKNOWN"
RESULT_CHOICES = (
    RESULT_SUCCESS,
    RESULT_MANUALLY_APPROVED,
    RESULT_DENIED,
    RESULT_TEMPORARY_FAILURE,
    RESULT_UNKNOWN,
)

# CyberSource REST export compliance decisions, returned as the `status` field of
# a /risk/v1/export-compliance-inquiries response.

# The screening ran to completion. This is *not* by itself a pass: a completed
# check still reports any sanctions-list matches in infoCodes.
DECISION_COMPLETED = "COMPLETED"
# The screening explicitly rejected the customer.
DECISION_DECLINED = "DECLINED"
# CyberSource could not process the request as sent, e.g. missing or malformed
# bill-to fields. Treated as a temporary failure: nothing is recorded and the
# caller is asked to try again, matching the old SOAP reasonCode 101/102 handling.
DECISION_INVALID_REQUEST = "INVALID_REQUEST"

DENIED_DECISIONS = [DECISION_DECLINED]
TEMPORARY_FAILURE_DECISIONS = [DECISION_INVALID_REQUEST]
