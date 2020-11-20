"""PDF Parsing functions for Vouchers"""
import json
import logging
from datetime import datetime
from uuid import uuid4
import difflib
import re

from django.conf import settings
from django.db.models import Q
import pdftotext

from courses.models import CourseRun
from ecommerce.api import get_valid_coupon_versions
from ecommerce.models import Company

log = logging.getLogger()


def remove_extra_spaces(text):
    """
    Remove extra spaces from text

    Args:
        text(str): The text to remove spaces from

    Returns:
        str: The text with extra spaces removed
    """
    if text:
        return re.sub(r"\s+", " ", text.strip())


def get_current_voucher(user):
    """
    Get the active voucher for a user
    Args:
        user (User): user to return voucher for

    Returns:
        Voucher: active voucher for user
    """
    return user.vouchers.order_by("uploaded").last()


def get_eligible_coupon_choices(voucher):
    """
    Find exact or partial matching course runs and get valid coupons for them

    Args:
        voucher (Voucher): a voucher to find courses for

    Returns:
        list of tuple:
            list of ('[<product_id>, <coupon_id>]', <course title>) for an eligible coupon / CourseRun match
    """
    course_matches = None
    # Search for an exact match if all inputs exist
    if voucher.course_id_input and voucher.course_title_input:
        course_matches = (
            CourseRun.objects.filter(
                course__readable_id__exact=voucher.course_id_input,
                course__title__exact=voucher.course_title_input,
                start_date__date=voucher.course_start_date_input,
            )
            .live()
            .available()
            .order_by("start_date")
        )

    # Search for partial matches if no exact match was found
    if course_matches is None or not course_matches.exists():
        # Try partial matching
        course_matches = (
            CourseRun.objects.filter(
                (
                    Q(course__readable_id__icontains=voucher.course_id_input)
                    if voucher.course_id_input
                    else Q()
                )
                | (
                    Q(course__title__icontains=voucher.course_title_input)
                    if voucher.course_title_input
                    else Q()
                )
                | Q(start_date__date=voucher.course_start_date_input)
            )
            .live()
            .available()
            .order_by("start_date")
        )

    if not course_matches.exists():
        # No partial matches found
        log.error("Found no matching course runs for voucher %s", voucher.id)
        return []

    # Check for valid coupon options and return choices
    valid_coupons = [
        get_valid_voucher_coupons_version(voucher, match.product.first())
        for match in course_matches
    ]
    eligible_choices = [
        (
            json.dumps(
                (course_matches[i].product.first().id, valid_coupons[i].coupon.id)
            ),
            "{title} - starts {start_date}".format(
                title=course_matches[i].title,
                start_date=course_matches[i].start_date.strftime("%b %d, %Y"),
            ),
        )
        for i in range(len(course_matches))
        if valid_coupons[i] is not None and course_matches[i].product is not None
    ]
    if course_matches and not eligible_choices:
        log.error("Found no valid coupons for matches for voucher %s", voucher.id)

    if len(eligible_choices) > 1 and voucher.course_title_input:
        eligible_choices_titles = [choice[1] for choice in eligible_choices]
        close_matches = difflib.get_close_matches(
            voucher.course_title_input,
            eligible_choices_titles,
            len(eligible_choices_titles),
            0,
        )
        sorted_eligible_choices = []
        for match in close_matches:
            sorted_eligible_choices.append(
                eligible_choices[eligible_choices_titles.index(match)]
            )
        eligible_choices = sorted_eligible_choices

    return eligible_choices


def get_valid_voucher_coupons_version(voucher, product):
    """
    Return valid coupon versions fo a voucher and product

    Args:
        voucher (Voucher): voucher provides the user to check coupons for
        product (Product): product to find coupons for

    Returns:
        (CouponVersion): a CouponVersion object that matches the product and is valid for the user and company
    """
    return (
        get_valid_coupon_versions(
            product,
            voucher.user,
            full_discount=True,
            company=Company.objects.get(id=settings.VOUCHER_COMPANY_ID),
        )
        .filter(coupon__voucher=None)
        .first()
    )


def read_pdf_domestic(pdf):
    """
    Process domestic vouchers and return parsed values
    """
    # These can be any row values that should be parsed from the voucher
    row_values = {
        settings.VOUCHER_DOMESTIC_EMPLOYEE_KEY: "",
        settings.VOUCHER_DOMESTIC_EMPLOYEE_ID_KEY: "",
    }

    # These column values are needed to parse the appropriate columns
    column_values = {
        settings.VOUCHER_DOMESTIC_KEY: "",
        settings.VOUCHER_DOMESTIC_COURSE_KEY: "",
        settings.VOUCHER_DOMESTIC_CREDITS_KEY: "",
        settings.VOUCHER_DOMESTIC_DATES_KEY: "",
        settings.VOUCHER_DOMESTIC_AMOUNT_KEY: "",
    }

    scanning_rows = False
    first_row = False

    for page in pdf:
        for line in page.splitlines():
            for row_name in row_values:
                if line.startswith(row_name):
                    elements = [e.strip() for e in line.split("  ") if e != ""]
                    if len(elements) > 1:
                        row_values[row_name] = elements[1]

            if line.startswith(settings.VOUCHER_DOMESTIC_KEY):
                start_positions = [line.index(val) for val in column_values]
                scanning_rows = True
                first_row = True
                continue
            if line.startswith("NOTE:"):
                scanning_rows = False

            if scanning_rows:
                elements = [
                    line[a:b].strip()
                    for a, b in zip(start_positions, start_positions[1:] + [None])
                ]
                update_column_values(column_values, elements)

                # Handle issue where credits are often incorrectly placed as part of the Course Name column
                if first_row:
                    last_val = column_values[
                        settings.VOUCHER_DOMESTIC_COURSE_KEY
                    ].split(" ")[-1]
                    try:
                        float(last_val)
                        column_values[
                            settings.VOUCHER_DOMESTIC_COURSE_KEY
                        ] = column_values[settings.VOUCHER_DOMESTIC_COURSE_KEY][
                            0 : column_values[
                                settings.VOUCHER_DOMESTIC_COURSE_KEY
                            ].index(last_val)
                        ]
                        column_values[settings.VOUCHER_DOMESTIC_CREDITS_KEY] = (
                            last_val
                            + column_values[settings.VOUCHER_DOMESTIC_CREDITS_KEY]
                        )
                    except ValueError:
                        pass

                    first_row = False

    row_values.update(column_values)
    return row_values


def update_column_values(column_values, elements):
    """
    Update column values with the sliced elements
    """
    if len(elements) == 5:
        for column, value in zip(column_values, elements):
            if value:
                if column_values[column]:
                    column_values[column] += " "
                column_values[column] += value


def read_pdf_international(pdf):
    """
    Process international vouchers and return parsed values
    """
    row_values = {
        settings.VOUCHER_INTERNATIONAL_EMPLOYEE_KEY: "",
        settings.VOUCHER_INTERNATIONAL_EMPLOYEE_ID_KEY: "",
        settings.VOUCHER_INTERNATIONAL_DATES_KEY: "",
        settings.VOUCHER_INTERNATIONAL_COURSE_NAME_KEY: "",
        settings.VOUCHER_INTERNATIONAL_COURSE_NUMBER_KEY: "",
    }
    extend_values = {}

    previous_line = ""
    recording_address = False
    for page in pdf:
        for line in page.splitlines():
            if line.startswith("To Whom It"):
                extend_values["Date"] = previous_line.strip()
            if line.startswith("Entity Name:"):
                extend_values["Entity Name"] = previous_line.strip()

            if line.startswith("School Instructions:"):
                recording_address = False
            if recording_address and "______" not in line:
                extend_values["Address"] += " " + line.strip()
            if line.startswith("Address:"):
                recording_address = True
                extend_values["Address"] = line.replace("Address:", "").strip()

            for row_name in row_values:
                if line.startswith(row_name):
                    row_values[row_name] = line.replace(row_name + ":", "").strip()
            previous_line = line
    row_values.update(extend_values)
    return row_values


def read_pdf(pdf_file):
    """
    Take in Voucher PDFs and parse them as either international or domestic, and return unified response.
    """
    domestic_settings_keys = [
        "VOUCHER_DOMESTIC_EMPLOYEE_KEY",
        "VOUCHER_DOMESTIC_EMPLOYEE_ID_KEY",
        "VOUCHER_DOMESTIC_KEY",
        "VOUCHER_DOMESTIC_COURSE_KEY",
        "VOUCHER_DOMESTIC_DATES_KEY",
    ]

    international_settings_keys = [
        "VOUCHER_INTERNATIONAL_EMPLOYEE_KEY",
        "VOUCHER_INTERNATIONAL_EMPLOYEE_ID_KEY",
        "VOUCHER_INTERNATIONAL_DATES_KEY",
        "VOUCHER_INTERNATIONAL_COURSE_NAME_KEY",
        "VOUCHER_INTERNATIONAL_COURSE_NUMBER_KEY",
    ]

    for key in domestic_settings_keys + international_settings_keys:
        if not getattr(settings, key):
            log.warning("Required setting %s missing for read_pdf", key)
            return
    try:
        pdf = pdftotext.PDF(pdf_file)
        if any("Entity Name:" in page for page in pdf):
            values = read_pdf_international(pdf)
            for key in international_settings_keys:
                if not values.get(getattr(settings, key)):
                    return None
            course_id_input = values.get(
                settings.VOUCHER_INTERNATIONAL_COURSE_NUMBER_KEY
            )
            return {
                "pdf": pdf_file,
                "employee_id": values.get(
                    settings.VOUCHER_INTERNATIONAL_EMPLOYEE_ID_KEY
                ),
                "voucher_id": None,
                "course_start_date_input": datetime.strptime(
                    values.get(settings.VOUCHER_INTERNATIONAL_DATES_KEY).split(" ")[0],
                    "%d-%b-%Y",
                ).date(),
                "course_id_input": remove_extra_spaces(course_id_input)
                if len(course_id_input) >= 3
                else "",
                "course_title_input": remove_extra_spaces(
                    values.get(settings.VOUCHER_INTERNATIONAL_COURSE_NAME_KEY)
                ),
                "employee_name": values.get(
                    settings.VOUCHER_INTERNATIONAL_EMPLOYEE_KEY
                ),
            }
        else:
            values = read_pdf_domestic(pdf)
            for key in domestic_settings_keys:
                if not values.get(getattr(settings, key)):
                    return None
            course_id_input = values.get(settings.VOUCHER_DOMESTIC_COURSE_KEY).split(
                " "
            )[0]
            return {
                "pdf": pdf_file,
                "employee_id": values.get(settings.VOUCHER_DOMESTIC_EMPLOYEE_ID_KEY),
                "voucher_id": values.get(settings.VOUCHER_DOMESTIC_KEY),
                "course_start_date_input": datetime.strptime(
                    values.get(settings.VOUCHER_DOMESTIC_DATES_KEY).split(" ")[0],
                    "%m/%d/%Y",
                ).date(),
                "course_id_input": remove_extra_spaces(course_id_input)
                if len(course_id_input) >= 3
                else "",
                "course_title_input": remove_extra_spaces(
                    " ".join(
                        values.get(settings.VOUCHER_DOMESTIC_COURSE_KEY).split(" ")[1:]
                    )
                ),
                "employee_name": values.get(settings.VOUCHER_DOMESTIC_EMPLOYEE_KEY),
            }
    except Exception:  # pylint: disable=broad-except
        log.exception("Could not parse PDF")
        return None


def voucher_upload_path(instance, filename):  # pylint: disable=unused-argument
    """
    Make a unique path/name for an uploaded voucher

    Args:
        instance(Voucher): the Voucher object
        filename(str): The voucher filename

    Returns:
        str: The unique filepath for the voucher
    """
    return "vouchers/{}_{}".format(uuid4(), filename)
