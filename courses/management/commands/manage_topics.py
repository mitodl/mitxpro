"""Management command to create topics from a CSV into the system OR assign topics to courses

## Arguments:
* --file <filename> - Path to the CSV file containing the topics OR the file containing the topics and courses titles (But only one at a time)
* --create-topics <filename> - Flag to decide that we should create topics from topics sheet (Format mentioned below)
* --assign-topics <filename> - Flag to decide that we should only populate topics from course title & topics sheet (Format mentioned below)

## Conditions for a valid topics file (Used for * --create-topics)
--file must be a valid CSV file. The command assumes that the file follows a specific format as mentioned below:

Parent Topic       | Parent Topic         | Parent Topic
subtopic           | subtopic             | subtopic
subtopic           | subtopic             | subtopic


## Conditions for a valid topics & titles file (Used for * --assign-topics)
--file must be a valid CSV file. The command assumes that the file would have a header row containing product_platform, product_name, High-Level Topic 1, Sub-topic 1, High-Level Topic 2, Sub-topic 2
The sample file format can be seen below:

product_platform   | product_name      | High-Level Topic 1        | Sub-topic 1       | High-Level Topic 2        | Sub-topic 2
xPRO               | Course title      | Parent Topic 1            | Subtopic 1        | Parent Topic 2            | Subtopic 2
Global Alumni      | Course title      | Parent Topic 1            | Subtopic 1        | Parent Topic 2            | Subtopic 2
Emeritus           | Course title      | Parent Topic 1            | Subtopic 1        | Parent Topic 2            | Subtopic 2


## Usage:
./manage.py --file <file_path> --create-topics
./manage.py --file <file_path> --assign-topics

"""

import csv
from pathlib import Path

from django.core.management import BaseCommand, CommandError

from cms.models import CoursePage, ExternalCoursePage
from courses.constants import DEFAULT_PLATFORM_NAME
from courses.models import CourseTopic

PLATFORM_COLUMN_NAME = "product_platform"
COURSE_TITLE_COLUMN_NAME = "product_name"
PARENT_TOPIC_1_COLUMN_NAME = "High-Level Topic 1"
SUB_TOPIC_1_COLUMN_NAME = "Sub-topic 1"
PARENT_TOPIC_2_COLUMN_NAME = "High-Level Topic 2"
SUB_TOPIC_2_COLUMN_NAME = "Sub-topic 2"

REQUIRED_COLUMNS = [
    PLATFORM_COLUMN_NAME,
    COURSE_TITLE_COLUMN_NAME,
    PARENT_TOPIC_1_COLUMN_NAME,
    SUB_TOPIC_1_COLUMN_NAME,
    PARENT_TOPIC_2_COLUMN_NAME,
    SUB_TOPIC_2_COLUMN_NAME,
]


def create_topic(name=None, parent=None):
    """Helper method to create topics based on topic/subtopic relationship"""
    name = name.strip()
    if not parent:
        return CourseTopic.objects.get_or_create(name=name)
    parent = parent.strip()
    parent_topic = CourseTopic.objects.parent_topics().get(name=parent)
    return CourseTopic.objects.get_or_create(name=name, parent=parent_topic)


def get_topic(name=None, parent=None):
    """Helper method to retrieve topics based on topic/subtopic relationship"""
    if name is None:
        return None
    name = name.strip()
    parent = parent.strip() if parent else None
    return CourseTopic.objects.filter(
        name__iexact=name, parent__name__iexact=parent
    ).first()


def perform_create_topics(file_path):
    """Read the data from the CSV file and create topics"""
    stats = {
        "new_topics": [],
        "skipped_topics": [],
        "new_subtopics": [],
        "skipped_subtopics": [],
    }

    with open(file_path) as topics_csv:  # noqa: PTH123
        data_dict = csv.DictReader(topics_csv)
        # Top level topic | Parent topics
        # data_dict.fieldnames are all the column names in the header of the CSV file.
        # We will create top level topics assuming each column name represents a top level topic.
        topics = data_dict.fieldnames

        for topic in topics:
            topic_obj, created = create_topic(topic)
            stats["new_topics"].append(topic_obj.name) if created else stats[
                "skipped_topics"
            ].append(topic_obj.name)

        # Each row after the header contains the subtopics respectively according to their parent in each column
        for row in data_dict:
            for topic, subtopic in row.items():
                if subtopic:
                    subtopic_obj, created = create_topic(subtopic, topic)
                    stats["new_subtopics"].append(
                        subtopic_obj.name
                    ) if created else stats["skipped_subtopics"].append(
                        subtopic_obj.name
                    )

        return stats


def perform_assign_topics(file_path):
    """Read the data from the CSV file and associate the topics to courses"""
    stats = []
    errors = []

    with open(file_path) as topics_csv:  # noqa: PTH123
        data_dict = csv.DictReader(topics_csv)
        # data_dict.fieldnames are all the column names in the header of the topics association CSV file.
        # Also, We want to scope the things while association so we will strictly need the right data. To make sure we have the
        # right data we will cross check that the sheet contains the required columns
        columns = data_dict.fieldnames
        if not all(required_column in columns for required_column in REQUIRED_COLUMNS):
            raise CommandError(
                "The file data is invalid. Please check file has all the columns."  # noqa: EM101
            )
        for row in data_dict:
            platform_name = row.get(PLATFORM_COLUMN_NAME)
            course_title = row.get(COURSE_TITLE_COLUMN_NAME)
            parent_topic1 = row.get(PARENT_TOPIC_1_COLUMN_NAME)
            sub_topic1 = row.get(SUB_TOPIC_1_COLUMN_NAME)
            parent_topic2 = row.get(PARENT_TOPIC_2_COLUMN_NAME)
            sub_topic2 = row.get(SUB_TOPIC_2_COLUMN_NAME)
            course_page = None
            course_page_cls = ExternalCoursePage
            if platform_name.lower() == DEFAULT_PLATFORM_NAME.lower():
                course_page_cls = CoursePage
            # Course titles can have trailing spaces so we would regex filter them instead of iexact
            course_pages = course_page_cls.objects.filter(
                title__regex=rf"(?i){course_title}\s*$",
                course__platform__name=platform_name,
            )

            if course_pages:
                parent_topic1 = get_topic(name=parent_topic1)
                sub_topic1 = (
                    get_topic(name=sub_topic1, parent=parent_topic1.name)
                    if parent_topic1
                    else None
                )
                parent_topic2 = get_topic(name=parent_topic2)
                sub_topic2 = (
                    get_topic(name=sub_topic2, parent=parent_topic2.name)
                    if parent_topic2
                    else None
                )

                for course_page in course_pages:
                    assigned_topics_stats = ""
                    skipped_topics_stats = ""
                    if parent_topic1:
                        course_page.topics.add(parent_topic1)
                        assigned_topics_stats = (
                            assigned_topics_stats + parent_topic1.name
                        )
                    if sub_topic1:
                        course_page.topics.add(sub_topic1)
                        assigned_topics_stats = (
                            assigned_topics_stats + ", " + sub_topic1.name
                        )

                    # If sub_topic 2 is blank we only assign High Level topic 1 and Subtopic 1 (See: https://github.com/mitodl/hq/issues/5841#issuecomment-2447413927)
                    if sub_topic2 and parent_topic2:
                        course_page.topics.add(parent_topic2)
                        course_page.topics.add(sub_topic2)
                        assigned_topics_stats = (
                            assigned_topics_stats
                            + ", "
                            + parent_topic2.name
                            + ", "
                            + sub_topic2.name
                        )

                    else:
                        skipped_topics_stats = (
                            skipped_topics_stats + parent_topic2.name
                            if parent_topic2
                            else None + "," + sub_topic2.name
                            if sub_topic2
                            else None
                        )
                    course_page.save()

                    stats.append(
                        f"{course_title}  |  Topics Assigned: {assigned_topics_stats}  |  Topics Skipped: {skipped_topics_stats or None}"
                    )
            else:
                errors.append(f"Course not found: {course_title}")
    return errors, stats


class Command(BaseCommand):
    """The command can performs two operations:
    1. Reads a list of topics/subtopics from a CSV file and loads them into system
    2. Reads a list of courses and topics from a CSV and associates topics to courses
    """

    help = """
    Manage the topics through a CSV

    Creating topics: ./manage.py --file <file_path> --create-topics
    Assigning topics: ./manage.py --file <file_path> --assign-topics
    """

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            help="Path to the CSV file",
            required=True,
            dest="topics_file",
        )
        parser.add_argument(
            "--create-topics",
            action="store_true",
            help="Perform the topics creation operation",
        )
        parser.add_argument(
            "--assign-topics",
            action="store_true",
            help="Perform the topics assignment operation",
        )

    def handle(self, *args, **options):  # noqa: ARG002
        """Handle command execution"""

        file_path = options["topics_file"].strip()
        arg_create_topics = options["create_topics"]
        arg_assign_topics = options["assign_topics"]

        if not any([arg_create_topics, arg_assign_topics]):
            raise CommandError(
                "Please select the operation to perform. Options are --create-topics or --assign-topics"  # noqa: EM101
            )
        if arg_create_topics and arg_assign_topics:
            raise CommandError("Only one operation is allowed.")  # noqa: EM101

        if not file_path or not file_path.endswith(".csv"):
            raise CommandError("The command can handle only CSV files")  # noqa: EM101

        if not Path(file_path).exists():
            raise CommandError("Invalid file path")  # noqa: EM101
        if arg_create_topics:
            # Perform the create topics operation
            stats = perform_create_topics(file_path=file_path)
            self.stdout.write(
                self.style.SUCCESS(f"Topics created: {stats['new_topics']}\n")
            )
            self.stdout.write(
                self.style.SUCCESS(f"Topics skipped: {stats['skipped_topics']}\n")
            )
            self.stdout.write(
                self.style.SUCCESS(f"Subtopics created: {stats['new_subtopics']}\n")
            )
            self.stdout.write(
                self.style.SUCCESS(f"Subtopics skipped: {stats['skipped_subtopics']}\n")
            )

        else:
            errors, stats = perform_assign_topics(file_path=file_path)
            for stat in stats:
                self.stdout.write(self.style.SUCCESS(f"{stat}\n"))

            for error in errors:
                self.stdout.write(self.style.ERROR(f"{error}\n"))
