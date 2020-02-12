"""Constants for the mail app"""

EMAIL_VERIFICATION = "verification"
EMAIL_PW_RESET = "password_reset"
EMAIL_BULK_ENROLL = "bulk_enroll"
EMAIL_COURSE_RUN_ENROLLMENT = "course_run_enrollment"
EMAIL_COURSE_RUN_UNENROLLMENT = "course_run_unenrollment"
EMAIL_B2B_RECEIPT = "b2b_receipt"
EMAIL_PRODUCT_ORDER_RECEIPT = "product_order_receipt"
EMAIL_CHANGE_EMAIL = "change_email"

EMAIL_TYPE_DESCRIPTIONS = {
    EMAIL_VERIFICATION: "Verify Email",
    EMAIL_PW_RESET: "Password Reset",
    EMAIL_BULK_ENROLL: "Bulk Enrollment",
    EMAIL_COURSE_RUN_ENROLLMENT: "Course Run Enrollment",
    EMAIL_B2B_RECEIPT: "Enrollment Code Purchase Receipt",
    EMAIL_CHANGE_EMAIL: "Change Email",
}

MAILGUN_API_DOMAIN = "api.mailgun.net"

MAILGUN_DELIVERED = "delivered"
MAILGUN_FAILED = "failed"
MAILGUN_OPENED = "opened"
MAILGUN_CLICKED = "clicked"
MAILGUN_EVENTS = [MAILGUN_DELIVERED, MAILGUN_FAILED, MAILGUN_OPENED, MAILGUN_CLICKED]
MAILGUN_EVENT_CHOICES = [(event, event) for event in MAILGUN_EVENTS]
