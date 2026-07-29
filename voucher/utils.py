"""PDF Parsing functions for Vouchers"""

import logging
import re
from datetime import datetime
from uuid import uuid4

import pdftotext
from django.conf import settings

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
    if text:  # noqa: RET503
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


def get_eligible_product_detail(voucher):
    """
    Find a matching course run and get a valid coupon for it

    Args:
        voucher (Voucher): a voucher to find course for

    Returns:
        tuple: <product_id>, <coupon_id>, <course run display title> for the eligible coupon / CourseRun match
    """
    matching_course_run = None
    if voucher.course_id_input and voucher.course_title_input:
        matching_course_run = (
            CourseRun.objects.filter(
                course__readable_id__iexact=voucher.course_id_input,
                course__title__iexact=voucher.course_title_input,
                start_date__date=voucher.course_start_date_input,
            )
            .live()
            .enrollment_available()
            .available()
            .order_by("start_date")
        ).first()

    if not matching_course_run:
        log.error("Found no matching course runs for voucher %s", voucher.id)
        return None, None, None

    valid_coupon = get_valid_voucher_coupons_version(
        voucher, matching_course_run.product.first()
    )
    if not valid_coupon:
        log.error(
            "Found no valid coupons for course run matching the voucher %s", voucher.id
        )
        return None, None, None

    return (
        matching_course_run.product.first().id,
        valid_coupon.coupon.id,
        f"{matching_course_run.title} - starts {matching_course_run.start_date.strftime('%b %d, %Y')}",
    )


def get_valid_voucher_coupons_version(voucher, product):
    """
    Return valid coupon versions for a voucher and product

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


def read_pdf_domestic(pdf):  # noqa: C901
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
            if len(line) > 0:
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
                            column_values[settings.VOUCHER_DOMESTIC_COURSE_KEY] = (
                                column_values[settings.VOUCHER_DOMESTIC_COURSE_KEY][
                                    0 : column_values[
                                        settings.VOUCHER_DOMESTIC_COURSE_KEY
                                    ].index(last_val)
                                ]
                            )
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
    if len(elements) == 5:  # noqa: PLR2004
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
            return  # noqa: RET502
    try:
        pdf = pdftotext.PDF(pdf_file, physical=True)
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
                "course_start_date_input": datetime.strptime(  # noqa: DTZ007
                    values.get(settings.VOUCHER_INTERNATIONAL_DATES_KEY).split(" ")[0],
                    "%d-%b-%Y",
                ).date(),
                "course_id_input": remove_extra_spaces(course_id_input)
                if len(course_id_input) >= 3  # noqa: PLR2004
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
                "course_start_date_input": datetime.strptime(  # noqa: DTZ007
                    values.get(settings.VOUCHER_DOMESTIC_DATES_KEY).split(" ")[0],
                    "%m/%d/%Y",
                ).date(),
                "course_id_input": remove_extra_spaces(course_id_input)
                if len(course_id_input) >= 3  # noqa: PLR2004
                else "",
                "course_title_input": remove_extra_spaces(
                    " ".join(
                        values.get(settings.VOUCHER_DOMESTIC_COURSE_KEY).split(" ")[1:]
                    )
                ),
                "employee_name": values.get(settings.VOUCHER_DOMESTIC_EMPLOYEE_KEY),
            }
    except Exception:
        log.exception("Could not parse PDF")
        return None


def voucher_upload_path(instance, filename):  # noqa: ARG001
    """
    Make a unique path/name for an uploaded voucher

    Args:
        instance(Voucher): the Voucher object
        filename(str): The voucher filename

    Returns:
        str: The unique filepath for the voucher
    """
    return f"vouchers/{uuid4()}_{filename}"
