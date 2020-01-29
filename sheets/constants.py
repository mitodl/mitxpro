"""Sheets app constants"""

from mail.constants import MAILGUN_FAILED

REQUIRED_GOOGLE_API_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
DEFAULT_GOOGLE_EXPIRE_TIMEDELTA = dict(minutes=60)

SHEETS_VALUE_REQUEST_PAGE_SIZE = 50
SHEET_TYPE_COUPON_REQUEST = "enrollrequest"
SHEET_TYPE_REFUND = "refund"
SHEET_TYPE_COUPON_ASSIGN = "enrollassign"

# The index of the first row of a spreadsheet according to Google
GOOGLE_SHEET_FIRST_ROW = 1
GOOGLE_AUTH_URI = "https://accounts.google.com/o/oauth2/auth"
GOOGLE_TOKEN_URI = "https://oauth2.googleapis.com/token"
GOOGLE_AUTH_PROVIDER_X509_CERT_URL = "https://www.googleapis.com/oauth2/v1/certs"
GOOGLE_DATE_TIME_FORMAT = "DATE_TIME"
GOOGLE_SERVICE_ACCOUNT_EMAIL_DOMAIN = "iam.gserviceaccount.com"
GOOGLE_API_NOTIFICATION_TYPE = "webhook"
GOOGLE_API_FILE_WATCH_KIND = "api#channel"
GOOGLE_API_TRUE_VAL = "TRUE"

ASSIGNMENT_MESSAGES_COMPLETED_KEY = "assignmentsCompleted"
ASSIGNMENT_MESSAGES_COMPLETED_DATE_KEY = "assignmentsCompletedDate"
ASSIGNMENT_SHEET_PREFIX = "Enrollment Codes"
ASSIGNMENT_SHEET_ENROLLED_STATUS = "enrolled"

REFUND_SHEET_ORDER_TYPE_FULL_COUPON = "Enrollment Code"
REFUND_SHEET_ORDER_TYPE_PAID = "Paid via Cybersource"
REFUND_SHEET_PROCESSOR_NAME = "MIT xPRO app"

MAILGUN_API_TIMEOUT_RETRIES = 3
INVALID_EMAIL_STATUS = "invalid"
UNKNOWN_EMAIL_ERROR_STATUS = "unrecognized error"
UNSENT_EMAIL_STATUSES = {
    None,
    INVALID_EMAIL_STATUS,
    MAILGUN_FAILED,
    UNKNOWN_EMAIL_ERROR_STATUS,
}
