"""Sheets app constants"""

REQUIRED_GOOGLE_API_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
GOOGLE_AUTH_URI = "https://accounts.google.com/o/oauth2/auth"
GOOGLE_TOKEN_URI = "https://oauth2.googleapis.com/token"
GOOGLE_AUTH_PROVIDER_X509_CERT_URL = "https://www.googleapis.com/oauth2/v1/certs"
ASSIGNMENT_PROCESSED_KEY = "processed"
ASSIGNMENT_PROCESSED_DATE_KEY = "processedDate"
ASSIGNMENT_COMPLETED_KEY = "assignmentsCompleted"
ASSIGNMENT_COMPLETED_DATE_KEY = "assignmentsCompletedDate"
GOOGLE_API_TRUE_VAL = "TRUE"
ASSIGNMENT_SHEET_PREFIX = "Bulk Coupons - "
