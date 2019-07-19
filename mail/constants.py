"""Constants for the mail app"""

EMAIL_VERIFICATION = "verification"
EMAIL_PW_RESET = "password_reset"
EMAIL_BULK_ENROLL = "bulk_enroll"
EMAIL_COURSE_RUN_ENROLLMENT = "course_run_enrollment"
EMAIL_COURSE_RUN_UNENROLLMENT = "course_run_unenrollment"

EMAIL_TYPE_DESCRIPTIONS = {
    EMAIL_VERIFICATION: "Verify Email",
    EMAIL_PW_RESET: "Password Reset",
    EMAIL_BULK_ENROLL: "Bulk Enrollment",
    EMAIL_COURSE_RUN_ENROLLMENT: "Course Run Enrollment",
}
