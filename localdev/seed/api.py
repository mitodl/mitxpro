"""Functions/classes for adding and removing seed data"""
import os
import json
from collections import defaultdict
from types import SimpleNamespace
from wagtail.core.models import Page

from django.conf import settings

from courses.models import Program, Course, CourseRun
from courses.serializers import ProgramSerializer, CourseSerializer, CourseRunSerializer
from mitxpro.utils import dict_without_keys, filter_dict_by_key_set, get_field_names
from cms.models import ProgramPage, CoursePage


COURSE_SEED_FILE_PATH = os.path.join(
    settings.BASE_DIR, "localdev/seed/resources/course_seed_data.json"
)


def get_top_level_wagtail_page():
    """
    The Wagtail CMS (at least in our usage) has one root page at depth 1, and one page at depth 2. All pages that we
    create in Wagtail are added as children to the page at depth 2.
    """
    return Page.objects.get(depth=2)


def delete_wagtail_pages(page_cls, filter_dict):
    """
    Completely deletes Wagtail CMS pages that match a filter. Wagtail overrides standard delete functionality,
    making it difficult to actually delete Page objects and get information about what was deleted.
    """
    page_ids_to_delete = (
        page_cls.objects.filter(**filter_dict).values_list("id", flat=True).all()
    )
    num_pages = len(page_ids_to_delete)
    base_pages_qset = Page.objects.filter(id__in=page_ids_to_delete)
    if not base_pages_qset.exists():
        return 0, {}
    base_pages_qset.delete()
    return (
        num_pages,
        {page_cls._meta.label: num_pages},  # pylint: disable=protected-access
    )


def filter_for_model_fields(model_cls, dict_to_filter):
    """Filters a dict to return only the keys that match fields in a model class"""
    model_field_names = get_field_names(model_cls)
    return filter_dict_by_key_set(dict_to_filter, model_field_names)


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
    # Maps a course model with some information about its associated Wagtail page class
    COURSE_MODEL_PAGE_PROPS = {
        Program: SimpleNamespace(
            page_cls=ProgramPage, page_field_name=ProgramPage.program.field.name
        ),
        Course: SimpleNamespace(
            page_cls=CoursePage, page_field_name=CoursePage.course.field.name
        ),
    }
    # String to prepend to a field value that will indicate seed data.
    SEED_DATA_PREFIX = "SEED"

    def __init__(self):
        self.seed_result = SeedResult()

    def _seed_prefixed(self, value):
        """Returns the same value with a prefix that indicates seed data"""
        return " ".join([self.SEED_DATA_PREFIX, value])

    def _seeded_field_and_value(self, model_cls, data):
        """
        Returns the field name and seed-adjusted value for some data that is being deserialized on some model

        Example return value: ("title", "SEED My Course Title")
        """
        field_name = self.SEED_DATA_FIELD_MAP[model_cls]
        seeded_value = self._seed_prefixed(data[field_name])
        return field_name, seeded_value

    def _deserialize(self, serializer_cls, data):
        """
        Attempts to deserialize and save an object if it doesn't already exist,
        and adds it to the results according to whether or not it was created.
        """
        model_cls = serializer_cls.Meta.model
        field_name, seeded_value = self._seeded_field_and_value(model_cls, data)
        existing_obj = model_cls.objects.filter(**{field_name: seeded_value}).first()
        if existing_obj:
            self.seed_result.add_existing(existing_obj)
            return existing_obj
        model_data = filter_for_model_fields(model_cls, data)
        serialized = serializer_cls(
            data={
                # Set 'live' to True for seeded objects by default
                "live": True,
                **model_data,
                field_name: seeded_value,
            }
        )
        serialized.is_valid(raise_exception=True)
        added_obj = serialized.save()
        self.seed_result.add_created(added_obj)
        return added_obj

    def _create_cms_page(self, model_obj, data):
        """
        Creates a Wagtail CMS page for some Program/Course if one doesn't exist
        """
        model_cls = model_obj.__class__
        cms_page_props = self.COURSE_MODEL_PAGE_PROPS[model_cls]
        cms_page_cls = cms_page_props.page_cls
        cms_page_field_name = cms_page_props.page_field_name
        existing_obj = cms_page_cls.objects.filter(
            **{cms_page_field_name: model_obj}
        ).first()
        if existing_obj:
            self.seed_result.add_existing(existing_obj)
            return existing_obj
        base_wagtail_page = get_top_level_wagtail_page()
        cms_model_data = filter_for_model_fields(cms_page_cls, data)
        # CMS pages have a title property as well. Use the seed-adjusted value for it
        field_name, seeded_value = self._seeded_field_and_value(model_cls, data)
        page_obj = cms_page_cls(
            **{
                cms_page_field_name: model_obj,
                **cms_model_data,
                field_name: seeded_value,
            }
        )
        added_obj = base_wagtail_page.add_child(instance=page_obj)
        self.seed_result.add_created(added_obj)
        return added_obj

    def _delete(self, model_cls, data):
        """
        Attempts to delete an object if it doesn't already exist, and adds it to
        the results if it was deleted.
        """
        field_name, seeded_value = self._seeded_field_and_value(model_cls, data)
        existing_obj = model_cls.objects.filter(**{field_name: seeded_value}).first()
        if not existing_obj:
            return 0, {}
        # If there are any Wagtail pages associated with this object that will be deleted,
        # delete the Wagtail pages first.
        cms_page_props = self.COURSE_MODEL_PAGE_PROPS[existing_obj.__class__]
        if cms_page_props:
            cms_page_cls = cms_page_props.page_cls
            cms_page_field_name = cms_page_props.page_field_name
            deleted_count, deleted_type_counts = delete_wagtail_pages(
                cms_page_cls, {cms_page_field_name: existing_obj}
            )
            self.seed_result.add_deleted(deleted_type_counts)
        deleted_count, deleted_type_counts = existing_obj.delete()
        self.seed_result.add_deleted(deleted_type_counts)
        return deleted_count, deleted_type_counts

    def create_seed_data(self, raw_data):
        """Idempotently creates seed data based on raw course data and returns results"""
        self.seed_result = SeedResult()
        for raw_program_data in raw_data["programs"]:
            # Create the Program and associated ProgramPage
            program = self._deserialize(ProgramSerializer, raw_program_data)
            self._create_cms_page(program, raw_program_data)

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
            # Create the Course and associated CoursePage
            course = self._deserialize(CourseSerializer, course_data)
            self._create_cms_page(course, course_data)
            for raw_course_run_data in course_runs_data:
                # Create the CourseRun
                self._deserialize(
                    CourseRunSerializer, {**raw_course_run_data, "course": course.id}
                )
        return self.seed_result

    def delete_seed_data(self, raw_course_data):
        """Deletes seed data based on raw course data"""
        self.seed_result = SeedResult()
        for course_data in raw_course_data["courses"]:
            self._delete(Course, course_data)
        for program_data in raw_course_data["programs"]:
            self._delete(Program, program_data)
        return self.seed_result


def get_raw_course_data_from_file():
    """Loads raw course data from our seed data file"""
    with open(COURSE_SEED_FILE_PATH) as f:
        return json.loads(f.read())
