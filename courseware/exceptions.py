"""Courseware exceptions"""


class CoursewareUserCreateError(Exception):
    """Exception creating the CoursewareUser"""


class OpenEdXOAuth2Error(Exception):
    """We were unable to obtain a refresh token from openedx"""


class NoEdxApiAuthError(Exception):
    """The user was expected to have an OpenEdxApiAuth object but does not"""
