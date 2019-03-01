import os
import json
from collections import namedtuple

from courses.models import Program
from courses.serializers import ProgramSerializer, CourseSerializer


PROJECT_PATH = os.path.abspath(os.path.dirname(__name__))
COURSE_DATA_JSON_PATH = os.path.join(
    PROJECT_PATH,
    "seed/resources/course_data.json"
)
FAKE_PROGRAM_DESC_PREFIX = "[FAKE] "
SeedResult = namedtuple("SeedResult", ["programs", "courses"])


def load_raw_course_data():
    with open(COURSE_DATA_JSON_PATH) as f:
        raw_course_data = json.loads(f.read())
    return raw_course_data


def load_and_deserialize_course_data():
    raw_course_data = load_raw_course_data()
    programs = []
    courses = []
    for program_data in raw_course_data["programs"]:
        serialized = ProgramSerializer(data=program_data)
        serialized.is_valid(raise_exception=True)
        programs.append(serialized.save())
    for course_data in raw_course_data["courses"]:
        program = (
            Program.objects.get(title=course_data["program"]).id
            if course_data.get("program") else None
        )
        course_data["program"] = program
        serialized = CourseSerializer(data=course_data)
        serialized.is_valid(raise_exception=True)
        courses.append(serialized.save())
    return SeedResult(programs=programs, courses=courses)
