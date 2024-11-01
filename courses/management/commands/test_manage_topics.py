import csv
from io import StringIO

import pytest
from django.core.management import CommandError, call_command

from cms.factories import CoursePageFactory, ExternalCoursePageFactory
from cms.models import CoursePage, ExternalCoursePage
from courses.constants import DEFAULT_PLATFORM_NAME
from courses.management.commands import manage_topics
from courses.models import CourseTopic, Platform


@pytest.mark.parametrize(
    "file_path, error_message",  # noqa: PT006
    [
        ("", "The command can handle only CSV files"),
        ("test", "The command can handle only CSV files"),
        ("test.txt", "The command can handle only CSV files"),
        ("test.csv", "Invalid file path"),
    ],
)
@pytest.mark.parametrize("operation_type", ["--create-topics", "--assign-topics"])
def test_command_args_file(file_path, error_message, operation_type):
    """Test that manage_topics command throws an error when no file path is provided"""
    with pytest.raises(CommandError) as command_error:
        call_command("manage_topics", operation_type, f"--file={file_path}")

    assert error_message in str(command_error.value)


def test_command_args_operation():
    """Test that manage_topics command throws an error when no file path is provided"""
    with pytest.raises(CommandError) as command_error:
        call_command("manage_topics", "--file=test.csv")
    assert (
        "Please select the operation to perform. Options are --create-topics or --assign-topics"
        in str(command_error.value)
    )

    with pytest.raises(CommandError) as command_error:
        call_command(
            "manage_topics", "--create-topics", "--assign-topics", "--file=test.csv"
        )
    assert "Only one operation is allowed." in str(command_error.value)


@pytest.mark.django_db
def test_command_create_topics():
    """Test that manage_topics command with "--create-topics" creates the topics properly when appropriate file is provided"""
    out = StringIO()
    call_command(
        "manage_topics",
        "--create-topics",
        "--file=courses/management/commands/resources/test_create_topics_data.csv",
        stdout=out,
    )

    topics = CourseTopic.objects.filter(parent__isnull=True)
    subtopics = CourseTopic.objects.filter(parent__isnull=False)
    assert subtopics.count() == 7
    assert topics.count() == 3
    assert f"Topics created: {[topic.name for topic in topics]}" in out.getvalue()
    assert f"Topics skipped: {[]}" in out.getvalue()
    assert (
        f"Subtopics created: {[subtopic.name for subtopic in subtopics]}"
        in out.getvalue()
    )
    assert f"Subtopics skipped: {[]}" in out.getvalue()

    # The operation should be idempotent. Running the command again should not create any new topics and the messages should be inverted
    out.truncate()
    call_command(
        "manage_topics",
        "--create-topics",
        "--file=courses/management/commands/resources/test_create_topics_data.csv",
        stdout=out,
    )
    assert f"Topics created: {[]}" in out.getvalue()
    assert f"Topics skipped: {[topic.name for topic in topics]}" in out.getvalue()
    assert f"Subtopics created: {[]}" in out.getvalue()
    assert (
        f"Subtopics skipped: {[subtopic.name for subtopic in subtopics]}"
        in out.getvalue()
    )

    # The operation should be idempotent. If a topic pre-exists, the command should not create it again
    out.truncate()
    existing_topic = topics.first()
    existing_subtopic = subtopics.first()
    # Delete all the topics except first and do likewise with subtopics
    topics.exclude(id__in=[existing_topic.id]).delete()
    subtopics.exclude(id__in=[existing_subtopic.id]).delete()
    # Run the command again and verify the stats
    call_command(
        "manage_topics",
        "--create-topics",
        "--file=courses/management/commands/resources/test_create_topics_data.csv",
        stdout=out,
    )

    topics = CourseTopic.objects.filter(parent__isnull=True)
    subtopics = CourseTopic.objects.filter(parent__isnull=False)

    assert (
        f"Topics created: {[topic.name for topic in topics.exclude(id=existing_topic.id)]}"
        in out.getvalue()
    )
    assert f"Topics skipped: {[existing_topic.name]}" in out.getvalue()
    assert (
        f"Subtopics created: {[subtopic.name for subtopic in subtopics.exclude(id=existing_subtopic.id)]}"
        in out.getvalue()
    )
    assert f"Subtopics skipped: {[existing_subtopic.name]}" in out.getvalue()


@pytest.mark.django_db
def test_command_assign_topics():  # noqa: C901
    """Test that manage_topics command with "--assign-topics" assigns the topics properly to courses when appropriate file is provided"""
    out = StringIO()
    # Validate that the assign topics accepts files with correct columns and format
    # test_create_topics_data.csv has an invalid format for assign topics operation
    with pytest.raises(CommandError) as command_error:
        call_command(
            "manage_topics",
            "--assign-topics",
            "--file=courses/management/commands/resources/test_create_topics_data.csv",
            stdout=out,
        )
    assert "The file data is invalid. Please check file has all the columns." in str(
        command_error.value
    )

    with open(  # noqa: PTH123
        "courses/management/commands/resources/test_assign_topics_data.csv"
    ) as topics_csv:
        data_dict = csv.DictReader(topics_csv)
        # Top level topic | Parent topics
        # data_dict.fieldnames are all the column names in the header of the CSV file.
        # We will create top level topics assuming each column name represents a top level topic.

        # Step 1: Iterating through the sheet to create the initial data. The validation would be tested in the next step
        for row in data_dict:
            platform_name = row.get(manage_topics.PLATFORM_COLUMN_NAME)
            course_title = row.get(manage_topics.COURSE_TITLE_COLUMN_NAME)
            parent_topic1 = row.get(manage_topics.PARENT_TOPIC_1_COLUMN_NAME)
            sub_topic1 = row.get(manage_topics.SUB_TOPIC_1_COLUMN_NAME)
            parent_topic2 = row.get(manage_topics.PARENT_TOPIC_2_COLUMN_NAME)
            sub_topic2 = row.get(manage_topics.SUB_TOPIC_2_COLUMN_NAME)
            platform, _ = Platform.objects.get_or_create(name=platform_name)
            if platform_name == DEFAULT_PLATFORM_NAME:
                CoursePageFactory.create(course__platform=platform, title=course_title)
            else:
                ExternalCoursePageFactory.create(
                    course__platform=platform,
                    title=course_title,
                    course__is_external=True,
                )

            if parent_topic1:
                parent_topic1, _ = CourseTopic.objects.get_or_create(name=parent_topic1)
            if sub_topic1:
                CourseTopic.objects.get_or_create(name=sub_topic1, parent=parent_topic1)
            if parent_topic2:
                parent_topic2, _ = CourseTopic.objects.get_or_create(name=parent_topic2)
            if sub_topic2:
                CourseTopic.objects.get_or_create(name=sub_topic2, parent=parent_topic2)

        call_command(
            "manage_topics",
            "--assign-topics",
            "--file=courses/management/commands/resources/test_assign_topics_data.csv",
            stdout=out,
        )
        topics_csv.seek(0)
        data_dict = csv.DictReader(topics_csv)
        # Step 2: Read the sheet again but this time we're verifying that the command assigned the correct topics to the courses
        for row in data_dict:
            platform_name = row.get(manage_topics.PLATFORM_COLUMN_NAME)
            course_title = row.get(manage_topics.COURSE_TITLE_COLUMN_NAME)
            parent_topic1 = row.get(manage_topics.PARENT_TOPIC_1_COLUMN_NAME)
            sub_topic1 = row.get(manage_topics.SUB_TOPIC_1_COLUMN_NAME)
            parent_topic2 = row.get(manage_topics.PARENT_TOPIC_2_COLUMN_NAME)
            sub_topic2 = row.get(manage_topics.SUB_TOPIC_2_COLUMN_NAME)
            if platform_name == DEFAULT_PLATFORM_NAME:
                course_page = CoursePage.objects.get(
                    title__iexact=course_title, course__platform__name=platform_name
                )
            else:
                course_page = ExternalCoursePage.objects.get(
                    title__iexact=course_title, course__platform__name=platform_name
                )

            course_topics = list(course_page.topics.values_list("name", flat=True))
            if parent_topic1:
                assert parent_topic1 in course_topics
            if sub_topic1:
                assert sub_topic1 in course_topics
            if not sub_topic2:
                assert parent_topic2 not in course_topics
                assert sub_topic2 not in course_topics
            else:
                assert parent_topic2 in course_topics
                assert sub_topic2 in course_topics
