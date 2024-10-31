from io import StringIO

import pytest
from django.core.management import CommandError, call_command

from courses.models import CourseTopic


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
    """Test that command creates the topics properly when appropriate file is provided"""
    out = StringIO()
    call_command(
        "manage_topics",
        "--create-topics",
        "--file=courses/management/commands/resources/test_topics_data.csv",
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
        "--file=courses/management/commands/resources/test_topics_data.csv",
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
        "--file=courses/management/commands/resources/test_topics_data.csv",
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
