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

ORDER_PREFIX = "XPRO-ORDER"

DISCOUNT_TYPE_PERCENT_OFF = "percent-off"
DISCOUNT_TYPE_DOLLARS_OFF = "dollars-off"

DISCOUNT_TYPES = [
    DISCOUNT_TYPE_PERCENT_OFF,
    DISCOUNT_TYPE_DOLLARS_OFF,
]

COUPON_ADD_PERMISSION = "ecommerce.add_coupon"
COUPON_UPDATE_PERMISSION = "ecommerce.change_coupon"

# Stripe event types we act on. `completed` only means the learner finished the
# checkout flow -- for payment methods with delayed notification the payment can
# still be processing -- so the async events matter as much as the first one.
STRIPE_EVENT_CHECKOUT_SESSION_COMPLETED = "checkout.session.completed"
STRIPE_EVENT_CHECKOUT_SESSION_EXPIRED = "checkout.session.expired"
STRIPE_EVENT_CHECKOUT_SESSION_ASYNC_PAYMENT_SUCCEEDED = (
    "checkout.session.async_payment_succeeded"
)
STRIPE_EVENT_CHECKOUT_SESSION_ASYNC_PAYMENT_FAILED = (
    "checkout.session.async_payment_failed"
)

STRIPE_FULFILL_EVENTS = [
    STRIPE_EVENT_CHECKOUT_SESSION_COMPLETED,
    STRIPE_EVENT_CHECKOUT_SESSION_ASYNC_PAYMENT_SUCCEEDED,
]
STRIPE_CANCEL_EVENTS = [
    STRIPE_EVENT_CHECKOUT_SESSION_EXPIRED,
    STRIPE_EVENT_CHECKOUT_SESSION_ASYNC_PAYMENT_FAILED,
]

# PaymentIntent statuses. The payment gateway library has constants for the
# checkout session and payment statuses, but not for these.
# https://docs.stripe.com/payments/paymentintents/lifecycle
STRIPE_INTENT_STATUS_CANCELED = "canceled"
STRIPE_INTENT_STATUS_PROCESSING = "processing"
STRIPE_INTENT_STATUS_REQUIRES_ACTION = "requires_action"
STRIPE_INTENT_STATUS_REQUIRES_CONFIRMATION = "requires_confirmation"
STRIPE_INTENT_STATUS_REQUIRES_PAYMENT_METHOD = "requires_payment_method"

# Overall states a Stripe checkout session is collapsed into. The session's own
# status fields don't tell the whole story -- the PaymentIntent carries the
# detail of the payment itself -- so both are considered together.
STRIPE_CHECKOUT_STATUS_PAID = "paid"
STRIPE_CHECKOUT_STATUS_PENDING = "pending"
STRIPE_CHECKOUT_STATUS_CANCELLED = "cancelled"
STRIPE_CHECKOUT_STATUS_ERROR = "error"
