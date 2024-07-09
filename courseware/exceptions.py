"""Courseware exceptions"""

from mitxpro.utils import get_error_response_summary


class EdxEnrollmentCreateError(Exception):
    """Exception creating the CoursewareUser"""


class CoursewareUserCreateError(Exception):
    """Exception creating the CoursewareUser"""


class OpenEdXOAuth2Error(Exception):
    """We were unable to obtain a refresh token from openedx"""


class NoEdxApiAuthError(Exception):
    """The user was expected to have an OpenEdxApiAuth object but does not"""


class EdxApiEnrollErrorException(Exception):  # noqa: N818
    """An edX enrollment API call resulted in an error response"""

    def __init__(self, user, course_run, http_error, msg=None):
        """
        Sets exception properties and adds a default message

        Args:
            user (users.models.User): The user for which the enrollment failed
            course_run (courses.models.CourseRun): The course run for which the enrollment failed
            http_error (requests.exceptions.HTTPError): The exception from the API call which contains
                request and response data.
        """
        self.user = user
        self.course_run = course_run
        self.http_error = http_error
        if msg is None:
            # Set some default useful error message
            msg = f"EdX API error enrolling user {self.user.username} ({self.user.email}) in course run '{self.course_run.courseware_id}'.\n{get_error_response_summary(self.http_error.response)}"
        super().__init__(msg)


class UnknownEdxApiEnrollException(Exception):  # noqa: N818
    """An edX enrollment API call failed for an unknown reason"""

    def __init__(self, user, course_run, base_exc, msg=None):
        """
        Sets exception properties and adds a default message

        Args:
            user (users.models.User): The user for which the enrollment failed
            course_run (courses.models.CourseRun): The course run for which the enrollment failed
            base_exc (Exception): The unexpected exception
        """
        self.user = user
        self.course_run = course_run
        self.base_exc = base_exc
        if msg is None:
            msg = f"Unexpected error enrolling user {self.user.username} ({self.user.email}) in course run '{self.course_run.courseware_id}' ({type(base_exc).__name__}: {base_exc!s})"
        super().__init__(msg)


class UserNameUpdateFailedException(Exception):  # noqa: N818
    """Raised if a user's profile name(Full Name) update call is failed"""


class EdxApiRegistrationValidationException(Exception):  # noqa: N818
    """An edX Registration Validation API call resulted in an error response"""

    def __init__(self, name, error_response, msg=None):
        """
        Sets exception properties and adds a default message

        Args:
            name (str): The name being validated
            response (requests.Response): edX response for name validation
        """
        self.name = name
        self.response = error_response
        if msg is None:
            # Set some default useful error message
            msg = f"EdX API error validating registration name {self.name}.\n{get_error_response_summary(self.response)}"
        super().__init__(msg)
