"""Ecommerce constants"""

# From secure acceptance documentation, under API reply fields:
# http://apps.cybersource.com/library/documentation/dev_guides/Secure_Acceptance_SOP/Secure_Acceptance_SOP.pdf
CYBERSOURCE_DECISION_ACCEPT = "ACCEPT"
CYBERSOURCE_DECISION_DECLINE = "DECLINE"
CYBERSOURCE_DECISION_REVIEW = "REVIEW"
CYBERSOURCE_DECISION_ERROR = "ERROR"
CYBERSOURCE_DECISION_CANCEL = "CANCEL"

REFERENCE_NUMBER_PREFIX = "xpro-b2c-"

# Any query that is prefetching an ordered set of related versions (ex: Product qset fetching
# related ProductVersions in reverse creation order) can use `to_attr` and this attribute name
# for the prefetched results.
ORDERED_VERSIONS_QSET_ATTR = "ordered_versions"

BULK_ENROLLMENT_EMAIL_TAG = "bulk_enrollment"
