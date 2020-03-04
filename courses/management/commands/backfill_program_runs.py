"""Management command to create program runs for programs that have a complete sets of course runs"""
import re
from collections import defaultdict

from django.contrib.auth import get_user_model
from django.core.management import BaseCommand

from courses.constants import TEXT_ID_RUN_TAG_PATTERN
from courses.models import Program, ProgramRun, CourseRun

User = get_user_model()


class Command(BaseCommand):
    """
    Creates program runs for programs that have a complete sets of course runs.
    Example: If there is a "+R1" course run for every course in the program, and no "R1" program run exists,
    this command will create that program run.
    """

    help = __doc__

    def add_arguments(self, parser):
        parser.add_argument(
            "-p",
            "--program",
            type=str,
            help="The 'readable_id' value for a Program (leave blank to backfill runs for all Programs)",
            required=False,
        )

    def get_complete_run_set_dates(self, program):
        """
        Builds a map of run suffixes (e.g.: "R1") mapped to the first start date and last end date
        of course runs that match that suffix, and only considers runs if there is one for each course
        in the program.

        Example return value:
        {
            R1: (<datetime.datetime>, <datetime.datetime>),
            R3: (<datetime.datetime>, <datetime.datetime>)
        }

        Args:
            program (Program): A Program object

        Returns:
            dict: A dictionary mapping a run suffix to a two-item tuple containing the overall
                start and end dates for the course runs matching that suffix.
        """
        course_ids = program.courses.values_list("id", flat=True)
        num_program_courses = len(course_ids)
        all_program_runs = (
            CourseRun.objects.filter(course_id__in=course_ids)
            .select_related("course")
            .order_by("course__position_in_program")
        )
        # Build a dict of run suffixes to a list of runs that have that suffix
        run_map = defaultdict(list)
        for run in all_program_runs:
            run_tag_match = re.search(TEXT_ID_RUN_TAG_PATTERN, run.courseware_id)
            if run_tag_match is not None:
                run_tag = run_tag_match.groupdict()["run_tag"]
                run_map[run_tag].append(run)

        # Validate run dates and add them to a dict if there are runs for every course in the program
        complete_run_map = {}
        for run_tag, all_program_runs in run_map.items():
            if len(all_program_runs) != num_program_courses:
                continue
            first_run, last_run = (all_program_runs[0], all_program_runs[-1])
            if first_run.start_date is None:
                self.stdout.write(
                    self.style.WARNING(
                        f"First run has no start date ({first_run}). Skipping..."
                    )
                )
            elif last_run.end_date is None:
                self.stdout.write(
                    self.style.WARNING(
                        f"Last run has no end date ({last_run}). Skipping..."
                    )
                )
            elif first_run.start_date > last_run.end_date:
                self.stdout.write(
                    self.style.WARNING(
                        f"First run start date is after the last run end date  ({first_run}, {last_run}). Skipping..."
                    )
                )
            complete_run_map[run_tag] = (first_run.start_date, last_run.end_date)

        return complete_run_map

    def backfill_runs_for_program(self, program):
        """
        Creates a ProgramRun for any set of course runs that (a) cover the full set of program courses,
        (b) have matching run tags, and (c) do not have a ProgramRun already associated.

        Args:
            program (Program): The program for which ProgramRuns will be created

        Returns:
            list of ProgramRun: The created ProgramRun objects
        """
        existing_program_run_tags = set(
            program.programruns.values_list("run_tag", flat=True)
        )
        complete_run_set_map = self.get_complete_run_set_dates(program)
        complete_run_tags = set(complete_run_set_map.keys())
        run_tags_to_create = complete_run_tags - existing_program_run_tags

        return [
            ProgramRun.objects.create(
                program=program,
                run_tag=run_tag,
                start_date=complete_run_set_map[run_tag][0],
                end_date=complete_run_set_map[run_tag][1],
            )
            for run_tag in run_tags_to_create
        ]

    def handle(self, *args, **options):
        """Handle command execution"""
        programs = Program.objects.prefetch_related("programruns", "courses")
        if options["program"]:
            programs = programs.filter(readable_id=options["program"])

        program_run_results = {}
        for program in programs:
            program_runs_created = self.backfill_runs_for_program(program)
            if program_runs_created:
                program_run_results[program] = program_runs_created

        if len(program_run_results) == 0:
            self.stdout.write(self.style.SUCCESS("No program runs created"))
        else:
            self.stdout.write(
                self.style.SUCCESS(f"{len(program_run_results)} program runs created:")
            )
            for program, program_runs in program_run_results.items():
                self.stdout.write(f"{program}:")
                for program_run in program_runs:
                    self.stdout.write(f"  - {program_run}")
