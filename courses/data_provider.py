from django.db.models import Prefetch, Q

from cms.models import CoursePage, ExternalCoursePage, ExternalProgramPage, ProgramPage
from courses.models import Course, CourseRun, Program
from ecommerce.models import Product
from mitxpro.utils import now_in_utc


class DataProvider:
    """This should serve as the source of truth for all course/program pages/django objects filters"""

    def get_courseware_filter(self, relative_filter="", sub_filter=""):
        """
        Generates course/program filter for the catalog visible and API consumable courses/programs.

        Args:
            relative_filter (str): A string representing the main filter
            sub_filter (str): A string representing the sub filter that combines with the main filter to do extra filtering

        Returns:
            Q: Returns a Q object to apply on course/program models

        """
        relative_filter = relative_filter + sub_filter

        courseware_live_filter = {
            f"{relative_filter}live": True,
            f"{relative_filter}courseruns__live": True,
        }
        courserun_start_date_filter = {
            f"{relative_filter}courseruns__start_date__isnull": False,
            f"{relative_filter}courseruns__start_date__gt": now_in_utc(),
        }
        courserun_enrollment_end_filter = {
            f"{relative_filter}courseruns__enrollment_end__isnull": False,
            f"{relative_filter}courseruns__enrollment_end__gt": now_in_utc(),
        }
        return Q(
            Q(**courseware_live_filter)
            & Q(Q(**courserun_start_date_filter) | Q(**courserun_enrollment_end_filter))
        )

    def get_data(self, filter_topic=None):
        """
        Method to get the data from the provider. Should be overridden in child classes

        Args:
            filter_topic (str): A string representing the the name of a topic

        Returns:
            QuerySet: Returns a QuerySet after applying all the filters
        """
        raise NotImplementedError


class CourseProvider(DataProvider):
    """Provider class to handle all Course (Django model) related queries"""

    def get_courses(self):
        """
        Generates list of courses based on certain filters

        Returns:
            QuerySet: Returns a QuerySet after applying all the filters
        """
        products_prefetch = Prefetch(
            "products", Product.objects.with_ordered_versions()
        )
        course_runs_prefetch = Prefetch(
            "courseruns", CourseRun.objects.prefetch_related(products_prefetch)
        )

        return (
            Course.objects.filter(
                self.get_courseware_filter(relative_filter=""), live=True
            )
            .select_related("coursepage", "externalcoursepage", "platform")
            .prefetch_related(
                "coursepage__topics",
                "externalcoursepage__topics",
                course_runs_prefetch,
            )
            .filter(Q(coursepage__live=True) | Q(externalcoursepage__live=True))
            .exclude(courseruns__products=None)
            .distinct()
        )

    def get_data(self, filter_topic=None):  # noqa: ARG002
        """
        Get course objects filtered w.r.t filter_topic (A topic Name)

        Args:
            filter_topic (str): A string representing the the name of a topic

        Returns:
            QuerySet: Returns a QuerySet after applying all the filters on Course model

        ** NOTE: The topic filter is not implemented here
        """
        return self.get_courses()


class ProgramProvider(DataProvider):
    """Provider class to handle all Program (Django model) related queries"""

    def get_programs(self):
        """
        Generates list of programs based on certain filters

        Returns:
            QuerySet: Returns a QuerySet after applying all the filters
        """
        products_prefetch = Prefetch(
            "products", Product.objects.with_ordered_versions()
        )
        course_runs_prefetch = Prefetch(
            "courseruns", CourseRun.objects.prefetch_related(products_prefetch)
        )
        courses_prefetch = Prefetch(
            "courses",
            Course.objects.select_related(
                "coursepage", "externalcoursepage", "platform"
            ).prefetch_related(
                course_runs_prefetch, "coursepage__topics", "externalcoursepage__topics"
            ),
        )

        return (
            Program.objects.filter(
                self.get_courseware_filter(relative_filter="courses__"), live=True
            )
            .exclude(products=None)
            .select_related("programpage", "externalprogrampage", "platform")
            .prefetch_related(courses_prefetch, products_prefetch)
            .filter(Q(programpage__live=True) | Q(externalprogrampage__live=True))
            .distinct()
        )

    def get_data(self, filter_topic=None):  # noqa: ARG002
        """
        Get course objects filtered w.r.t filter_topic (A topic Name)

        Args:
            filter_topic (str): A string representing the the name of a topic

        Returns:
            QuerySet: Returns a QuerySet after applying all the filters on Program model

        ** NOTE: The topic filter is not implemented here
        """

        return self.get_programs()


class CoursePageProvider(DataProvider):
    """Provider class to handle all Course Pages (CMS model) related queries"""

    def get_course_pages(self, page_cls):
        """
        Get course pages based on the provided page_cls)

        Args:
            page_cls (CoursePage | ExternalCoursePage): A class representing the page model to query

        Returns:
            List: Returns a list after applying all the filters on CoursePage/ExternalCoursePage model
        """

        return (
            page_cls.objects.live()
            .filter(
                (self.get_courseware_filter(relative_filter="course__")),
            )
            .order_by("id")
            .select_related("course")
            .distinct()
        )

    def get_internal_pages(self):
        """Support method to get internal course pages"""
        return self.get_course_pages(CoursePage)

    def get_external_pages(self):
        """Support method to get external course pages"""
        return self.get_course_pages(ExternalCoursePage)

    def get_data(self, filter_topic=None):
        """
        Get course pages filtered w.r.t filter_topic (A topic Name)

        Args:
            filter_topic (str): A string representing the the name of a topic

        Returns:
            List: Returns a list after applying all the filters on CoursePage/ExternalCoursePage model
        """

        internal_pages_qset = self.get_internal_pages()
        external_pages_qset = self.get_external_pages()

        if filter_topic is None:
            return list(internal_pages_qset) + list(external_pages_qset)

        internal_topic_filtered_qset = internal_pages_qset.filter(
            Q(topics__name=filter_topic) | Q(topics__parent__name=filter_topic)
        ).distinct()

        external_topic_filtered_qset = external_pages_qset.filter(
            Q(topics__name=filter_topic) | Q(topics__parent__name=filter_topic)
        ).distinct()
        return list(internal_topic_filtered_qset) + list(external_topic_filtered_qset)


class ProgramPageProvider(DataProvider):
    """Provider class to handle all Program Pages (CMS model) related queries"""

    def get_program_pages(self, page_cls):
        """
        Get program pages based on the provided page_cls (Possible Values: ProgramPage | ExternalProgramPage))

        Args:
            page_cls (ProgramPage | ExternalProgramPage): A class representing the Program page model to query

        Returns:
            List: Returns a list after applying all the filters on ProgramPage/ExternalProgramPage model
        """

        if page_cls == ProgramPage:
            prefetch_type = "coursepage"
        else:
            prefetch_type = "externalcoursepage"

        return (
            page_cls.objects.live()
            .filter(
                (self.get_courseware_filter(relative_filter="program__courses__")),
                program__live=True,
            )
            .order_by("id")
            .select_related("program")
            .prefetch_related(
                Prefetch(
                    "program__courses",
                    Course.objects.order_by("position_in_program").select_related(
                        prefetch_type
                    ),
                ),
            )
            .distinct()
        )

    def get_internal_pages(self):
        """Support method to get internal program pages"""
        return self.get_program_pages(ProgramPage)

    def get_external_pages(self):
        """Support method to get external program pages"""
        return self.get_program_pages(ExternalProgramPage)

    def get_data(self, filter_topic=None):
        """
        Get program pages filtered w.r.t filter_topic (A topic Name)

        Args:
            filter_topic (str): A string representing the the name of a topic

        Returns:
            List: Returns a list after applying all the filters on ProgramPage/ExternalProgramPage model
        """
        internal_pages_qset = self.get_internal_pages()
        external_pages_qset = self.get_external_pages()

        if filter_topic is None:
            return list(internal_pages_qset) + list(external_pages_qset)

        internal_topic_filtered_qset = internal_pages_qset.filter(
            Q(program__courses__coursepage__topics__name=filter_topic)
            | Q(program__courses__coursepage__topics__parent__name=filter_topic)
        ).distinct()

        external_topic_filtered_qset = external_pages_qset.filter(
            Q(program__courses__coursepage__topics__name=filter_topic)
            | Q(program__courses__coursepage__topics__parent__name=filter_topic)
        ).distinct()
        return list(internal_topic_filtered_qset) + list(external_topic_filtered_qset)
