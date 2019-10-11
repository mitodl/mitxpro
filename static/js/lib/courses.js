import * as R from "ramda"
import moment from "moment"

import {
  formatPrettyDate,
  formatPrettyDateTimeAmPm,
  firstItem,
  secondItem,
  parseDateString,
  getMinDate,
  getMaxDate
} from "./util"

import type Moment from "moment"
import type {
  CourseRunEnrollment,
  ProgramEnrollment
} from "../flow/courseTypes"

type DateSummary = {
  text: string,
  inProgress: boolean
}

export const getDateSummary = (
  courseRunEnrollment: CourseRunEnrollment
): DateSummary => {
  const now = moment()
  const startDate = parseDateString(courseRunEnrollment.run.start_date)
  if (startDate && startDate.isAfter(now)) {
    return {
      text:       `Starts: ${formatPrettyDateTimeAmPm(startDate)}`,
      inProgress: false
    }
  }
  const expirationDate = parseDateString(
    courseRunEnrollment.run.expiration_date
  )
  if (expirationDate && expirationDate.isBefore(now)) {
    return {
      text:       `Access Expired on: ${formatPrettyDate(expirationDate)}`,
      inProgress: false
    }
  }
  const endDate = parseDateString(courseRunEnrollment.run.end_date)
  if (endDate) {
    if (endDate.isAfter(now)) {
      return {
        text:       `Ends: ${formatPrettyDateTimeAmPm(endDate)}`,
        inProgress: true
      }
    } else {
      return {
        text:       `Ended: ${formatPrettyDate(endDate)}`,
        inProgress: false,
        archived:   true
      }
    }
  } else if (startDate) {
    return {
      text:       `Started: ${formatPrettyDate(startDate)}`,
      inProgress: true
    }
  } else {
    return {
      text:       "Start and end dates pending",
      inProgress: false
    }
  }
}

export const programDateRange = (
  programEnrollment: ProgramEnrollment
): Array<?Moment> => {
  const runDatePairs = R.compose(
    R.map(run => [
      parseDateString(run.start_date),
      parseDateString(run.end_date)
    ]),
    R.map(R.prop("run"))
  )(programEnrollment.course_run_enrollments)
  const minDate = getMinDate(R.map(firstItem, runDatePairs))
  const maxDate = getMaxDate(R.map(secondItem, runDatePairs))
  return [minDate, maxDate]
}
