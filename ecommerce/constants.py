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

CYBERSOURCE_CARD_TYPES = {
    "001": "Visa",
    "002": "Mastercard",
    "003": "American Express",
    "004": "Discover",
    "005": "Diners Club",
    "006": "Carte Blanche",
    "007": "JCB",
    "014": "Enroute",
    "021": "JAL",
    "024": "Maestro (UK)",
    "031": "Delta",
    "033": "Visa Electron",
    "034": "Dankort",
    "036": "Carte Bancaires",
    "037": "Carta Si",
    "039": "EAN",
    "040": "UATP",
    "042": "Maestro (Intl)",
    "050": "Hipercard",
    "051": "Aura",
    "054": "Elo",
    "061": "RuPay",
    "062": "China UnionPay",
}
