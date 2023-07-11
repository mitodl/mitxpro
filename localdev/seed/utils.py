import re

from localdev.seed.exceptions import InvalidCoursewareKeyFormat


def validate_courseware_id(courseware_id):
    invalid_courseware_re = re.compile("course.*?\+[a-zA-Z0-9-]+?\+[a-zA-Z0-9-_]+\+")

    if courseware_id and invalid_courseware_re.match(courseware_id):
        raise InvalidCoursewareKeyFormat(f"Invalid courseware key: {courseware_id}")
