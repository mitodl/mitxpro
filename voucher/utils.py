"""PDF Parsing functions for Vouchers"""

import logging
import pdftotext

from django.conf import settings

log = logging.getLogger()


def read_pdf_domestic(pdf):
    """
    Process domestic vouchers and return parsed values
    """
    row_values = {
        settings.VOUCHER_DOMESTIC_DATE_KEY: "",
        settings.VOUCHER_DOMESTIC_EMPLOYEE_KEY: "",
        settings.VOUCHER_DOMESTIC_EMPLOYEE_ID_KEY: "",
    }

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
            elif line.startswith("NOTE:"):
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
        settings.VOUCHER_INTERNATIONAL_PROGRAM_KEY: "",
        settings.VOUCHER_INTERNATIONAL_COURSE_KEY: "",
        settings.VOUCHER_INTERNATIONAL_SCHOOL_KEY: "",
        settings.VOUCHER_INTERNATIONAL_EMPLOYEE_ID_KEY: "",
        settings.VOUCHER_INTERNATIONAL_AMOUNT_KEY: "",
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
    if not (
        settings.VOUCHER_DOMESTIC_DATE_KEY
        and settings.VOUCHER_DOMESTIC_EMPLOYEE_KEY
        and settings.VOUCHER_DOMESTIC_EMPLOYEE_ID_KEY
        and settings.VOUCHER_DOMESTIC_KEY
        and settings.VOUCHER_DOMESTIC_COURSE_KEY
        and settings.VOUCHER_DOMESTIC_CREDITS_KEY
        and settings.VOUCHER_DOMESTIC_DATES_KEY
        and settings.VOUCHER_DOMESTIC_AMOUNT_KEY
        and settings.VOUCHER_INTERNATIONAL_EMPLOYEE_KEY
        and settings.VOUCHER_INTERNATIONAL_PROGRAM_KEY
        and settings.VOUCHER_INTERNATIONAL_COURSE_KEY
        and settings.VOUCHER_INTERNATIONAL_SCHOOL_KEY
        and settings.VOUCHER_INTERNATIONAL_EMPLOYEE_ID_KEY
        and settings.VOUCHER_INTERNATIONAL_AMOUNT_KEY
        and settings.VOUCHER_INTERNATIONAL_DATES_KEY
        and settings.VOUCHER_INTERNATIONAL_COURSE_NAME_KEY
        and settings.VOUCHER_INTERNATIONAL_COURSE_NUMBER_KEY
    ):
        log.warning("Required settings missing for read_pdf")
        return
    try:
        pdf = pdftotext.PDF(pdf_file)
        if any("Entity Name:" in page for page in pdf):
            values = read_pdf_international(pdf)
            return {
                "BEMSID": values.get(settings.VOUCHER_INTERNATIONAL_EMPLOYEE_ID_KEY),
                "voucher_id": None,
                "course_start_date": values.get(
                    settings.VOUCHER_INTERNATIONAL_DATES_KEY
                ).split(" ")[0],
                "class_module_number": values.get(
                    settings.VOUCHER_INTERNATIONAL_COURSE_NUMBER_KEY
                ),
                "class_module_title": values.get(
                    settings.VOUCHER_INTERNATIONAL_COURSE_NAME_KEY
                ),
                "employee_name": values.get(
                    settings.VOUCHER_INTERNATIONAL_EMPLOYEE_KEY
                ),
            }
        else:
            values = read_pdf_domestic(pdf)
            return {
                "BEMSID": values.get(settings.VOUCHER_DOMESTIC_EMPLOYEE_ID_KEY),
                "voucher_id": values.get(settings.VOUCHER_DOMESTIC_KEY),
                "course_start_date": values.get(
                    settings.VOUCHER_DOMESTIC_DATES_KEY
                ).split(" ")[0],
                "class_module_number": values.get(
                    settings.VOUCHER_DOMESTIC_COURSE_KEY
                ).split(" ")[0],
                "class_module_title": " ".join(
                    values.get(settings.VOUCHER_DOMESTIC_COURSE_KEY).split(" ")[1:]
                ),
                "employee_name": values.get(settings.VOUCHER_DOMESTIC_EMPLOYEE_KEY),
            }
    except Exception:  # pylint: disable=broad-except
        log.error("Could not parse PDF")
        return None
