from io import StringIO

import pytest
from django.core.management import CommandError, call_command

from courses.models import CourseTopic


def test_command_no_args():
    """Test that bulk load command throws and error when no file path is provided"""
    with pytest.raises(CommandError) as command_error:
        call_command("bulk_load_topics", "--file=")
    assert "Invalid file path" in str(command_error.value)


def test_command_no_csv_path_args():
    """Test that bulk load command throws and error when no CSV path is provided"""
    with pytest.raises(CommandError) as command_error:
        call_command("bulk_load_topics", "--file=test")
    assert "The command can handle only CSV files" in str(command_error.value)


@pytest.mark.django_db
def test_command_valid_csv():
    """Test that command creates the topics properly when appropriate file is provided"""
    out = StringIO()
    call_command(
        "bulk_load_topics",
        "--file=courses/management/commands/resources/test_topics_data.csv",
        stdout=out,
    )

    topics = CourseTopic.objects.filter(parent__isnull=True)
    subtopics = CourseTopic.objects.filter(parent__isnull=False)
    assert subtopics.count() == 7
    assert topics.count() == 3
    assert f"Topics created: {[topic.name for topic in topics]}" in out.getvalue()
    assert f"Topics skipped: {[]}" in out.getvalue()
    assert f"Subtopics created: {[topic.name for topic in subtopics]}" in out.getvalue()
    assert f"Subtopics skipped: {[]}" in out.getvalue()

    # Running the command again should not create any new topics and the messages should be inverted
    call_command(
        "bulk_load_topics",
        "--file=courses/management/commands/resources/test_topics_data.csv",
        stdout=out,
    )
    assert f"Topics created: {[]}" in out.getvalue()
    assert f"Topics skipped: {[topic.name for topic in topics]}" in out.getvalue()
    assert f"Subtopics created: {[]}" in out.getvalue()
    assert f"Subtopics skipped: {[topic.name for topic in subtopics]}" in out.getvalue()
