"""Functions/classes for adding and removing seed data"""
import os
import json
from collections import defaultdict

from django.conf import settings

from courses.models import Program, Course, CourseRun
from courses.serializers import ProgramSerializer, CourseSerializer, CourseRunSerializer
from mitxpro.utils import dict_without_keys


COURSE_SEED_FILE_PATH = os.path.join(
    settings.BASE_DIR, "localdev/seed/resources/course_seed_data.json"
)


class SeedResult:
    """Represents the results of seeding/unseeding"""

    def __init__(self):
        self.created = defaultdict(int)
        self.existing = defaultdict(int)
        self.deleted = defaultdict(int)

    def add_created(self, obj):
        """Adds to the count of created object types"""
        self.created[obj.__class__.__name__] += 1

    def add_existing(self, obj):
        """Adds to the count of existing object types"""
        self.existing[obj.__class__.__name__] += 1

    def add_deleted(self, deleted_type_dict):
        """Adds to the count of deleted object types"""
        for deleted_type, deleted_count in deleted_type_dict.items():
            self.deleted[deleted_type] += deleted_count

    @property
    def report(self):
        """Simple dict representing the seed result"""
        return {
            "Created": dict(self.created),
            "Already Existed": dict(self.existing),
            "Deleted": dict(self.deleted),
        }

    def __repr__(self):
        return str(self.report)


class SeedDataLoader:
    """Handles creation/deletion of seed data based on raw data"""

    # Our legacy course models did not enforce uniqueness on any fields. It's possible that
    # we'll want to change that, but for now this dict exists to indicate which field should
    # be used to (a) find an existing object for some data we're deserializing, and
    # (b) prepend a string indicating that the object is seed data.
    SEED_DATA_FIELD_MAP = {Program: "title", Course: "title", CourseRun: "title"}
    # String to prepend to a field value that will indicate seed data.
    SEED_DATA_PREFIX = "SEED"

    def __init__(self):
        self.seed_result = SeedResult()

    def _seed_prefixed(self, value):
        """Returns the same value with a prefix that indicates seed data"""
        return " ".join([self.SEED_DATA_PREFIX, value])

    def _deserialize(self, serializer_cls, data):
        """
        Attempts to deserialize and save an object if it doesn't already exist,
        and adds it to the results according to whether or not it was created.
        """
        model_cls = serializer_cls.Meta.model
        field_name = self.SEED_DATA_FIELD_MAP[model_cls]
        adjusted_value = self._seed_prefixed(data[field_name])
        existing_obj = model_cls.objects.filter(**{field_name: adjusted_value}).first()
        if existing_obj:
            self.seed_result.add_existing(existing_obj)
            return existing_obj
        serialized = serializer_cls(data={**data, field_name: adjusted_value})
        serialized.is_valid(raise_exception=True)
        added_obj = serialized.save()
        self.seed_result.add_created(added_obj)
        return added_obj

    def _delete(self, model_cls, data):
        """
        Attempts to delete an object if it doesn't already exist, and adds it to
        the results if it was deleted.
        """
        field_name = self.SEED_DATA_FIELD_MAP[model_cls]
        adjusted_value = self._seed_prefixed(data[field_name])
        existing_obj = model_cls.objects.filter(**{field_name: adjusted_value}).first()
        if not existing_obj:
            return 0, {}
        deleted_count, deleted_type_counts = existing_obj.delete()
        self.seed_result.add_deleted(deleted_type_counts)
        return deleted_count, deleted_type_counts

    def create_seed_data(self, raw_data):
        """Creates seed data based on raw course data"""
        self.seed_result = SeedResult()
        for raw_program_data in raw_data["programs"]:
            self._deserialize(ProgramSerializer, raw_program_data)

        for raw_course_data in raw_data["courses"]:
            # If a Course should belong to a Program, the value for the Course's "program" key
            # will be the Program's title
            program_title = raw_course_data.get("program")
            program = (
                Program.objects.get(title=self._seed_prefixed(program_title)).id
                if program_title
                else None
            )
            course_runs_data = raw_course_data.get("course_runs", [])
            course_data = {
                **dict_without_keys(raw_course_data, "course_runs"),
                "program": program,
            }
            course = self._deserialize(CourseSerializer, course_data)
            for raw_course_run_data in course_runs_data:
                self._deserialize(
                    CourseRunSerializer, {**raw_course_run_data, "course": course.id}
                )
        return self.seed_result

    def delete_seed_data(self, raw_course_data):
        """Deletes seed data based on raw course data"""
        self.seed_result = SeedResult()
        for program_data in raw_course_data["programs"]:
            self._delete(Program, program_data)
        for course_data in raw_course_data["courses"]:
            self._delete(Course, course_data)
        return self.seed_result


def get_raw_course_data_from_file():
    """Loads raw course data from our seed data file"""
    with open(COURSE_SEED_FILE_PATH) as f:
        return json.loads(f.read())
