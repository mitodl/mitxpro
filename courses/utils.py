"""
Utilities for courses/certificates
"""
from courses.models import CourseRunGrade, CourseRunCertificate


def ensure_course_run_grade(user, course_run, edx_grade, should_update=False):
    """
    Ensure that the local grades repository has the grade for the User/CourseRun combination supplied.

    Args:
        user (user.models.User): The user for whom the grade is being synced
        course_run (courses.models.CourseRun): The course run for which the grade is created
        edx_grade (edx_api.grades.models.UserCurrentGrade): The OpenEdx grade object
        should_update (bool): Update the local grade record if it exists

    Returns:
        (courses.models.CourseRunGrade, bool, bool) that depicts the CourseRunGrade, created and updated values
    """
    grade_properties = {
        "grade": edx_grade.percent,
        "passed": edx_grade.passed,
        "letter_grade": edx_grade.letter_grade,
    }

    updated = False
    if should_update:
        grade, created = CourseRunGrade.objects.update_or_create(
            course_run=course_run, user=user, defaults=grade_properties
        )
        updated = not created
    else:
        grade, created = CourseRunGrade.objects.get_or_create(
            course_run=course_run, user=user, defaults=grade_properties
        )
    return grade, created, updated


def process_course_run_grade_certificate(course_run_grade):
    """
    Ensure that the couse run certificate is in line with the values in the course run grade

    Args:
        course_run_grade (courses.models.CourseRunGrade): The course run grade for which to generate/delete the certificate

    Returns:
        (courses.models.CourseRunCertificate, bool, bool) that depicts the CourseRunCertificate, created, deleted values
    """
    user = course_run_grade.user
    course_run = course_run_grade.course_run
    should_delete = not bool(course_run_grade.grade)

    if should_delete:
        delete_count, _ = CourseRunCertificate.objects.filter(
            user=user, course_run=course_run
        ).delete()
        return None, False, (delete_count > 0)
    else:
        certificate, created = CourseRunCertificate.objects.get_or_create(
            user=user, course_run=course_run
        )
        return certificate, created, False
