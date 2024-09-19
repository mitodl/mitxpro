"""Management command to load bulk load topics from a CSV into system

Arguments:
* --file <filename> - Path to the CSV file containing the topics

--file must be a valid CSV file. The command assumes that the file would have a header row containing all the topics/subtopics.
The sample file format can be seen below:

topic       | topic         | topic
subtopic    | subtopic      | subtopic
subtopic    | subtopic      | subtopic

"""

import csv

from django.core.management import BaseCommand, CommandError

from courses.models import CourseTopic


def create_topic(name=None, parent=None):
    """Helper method to create topics based on topic/subtopic relationship"""
    name = name.strip()
    if not parent:
        return CourseTopic.objects.get_or_create(name=name)
    parent = parent.strip()
    parent_topic = CourseTopic.objects.get(name=parent, parent__isnull=True)
    return CourseTopic.objects.get_or_create(name=name, parent=parent_topic)


class Command(BaseCommand):
    """The command reads a list of topics/subtopics from a CSV file and loads them into system"""

    help = "Bulk loads the topics from a CSV file"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            help="Path to the CSV file containing topics",
            required=True,
            dest="topics_file",
        )

    def handle(self, *args, **options):  # noqa: ARG002
        """Handle command execution"""

        file_path = options["topics_file"].strip()
        if not file_path:
            raise CommandError("Invalid file path")  # noqa: EM101

        if not file_path.endswith(".csv"):
            raise CommandError("The command can handle only CSV files")  # noqa: EM101

        with open(file_path) as import_raw:  # noqa: PTH123
            data_dict = csv.DictReader(import_raw)
            # Top level topic | Parent topics
            # data_dict.fieldnames are all the column names in the header of the CSV file.
            # We will create top level topics assuming each column name represents a top level topic.
            topics = data_dict.fieldnames
            stats = {
                "new_topics": [],
                "skipped_topics": [],
                "new_subtopics": [],
                "skipped_subtopics": [],
            }

            for topic in topics:
                topic_obj, created = create_topic(topic)
                stats["new_topics"].append(topic_obj.name) if created else stats[
                    "skipped_topics"
                ].append(topic_obj.name)

            # Each row after the header contains the subtopics respectively according to their parent in each column
            for row in data_dict:
                for topic in topics:
                    subtopic = row.get(topic, "")
                    if subtopic:
                        subtopic_obj, created = create_topic(subtopic, topic)
                        stats["new_subtopics"].append(
                            subtopic_obj.name
                        ) if created else stats["skipped_subtopics"].append(
                            subtopic_obj.name
                        )

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
