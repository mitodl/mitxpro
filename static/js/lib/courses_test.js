// @flow
import * as R from "ramda"
import { assert } from "chai"
import moment from "moment"

import * as coursesApi from "./courses"
import {
  makeCourseRunEnrollment,
  makeProgramEnrollment
} from "../factories/course"
import { formatPrettyDate, formatPrettyDateTimeAmPm } from "./util"

describe("courses API function", () => {
  describe("programDateRange", () => {
    it("returns a two-item list containing the earliest start date and latest end date", () => {
      const now = moment()
      // Create course run enrollments for a program, and set all start and end dates to now
      const programRunEnrollments = R.compose(
        R.map(
          R.mergeDeepLeft({
            run: { start_date: now.toISOString(), end_date: now.toISOString() }
          })
        ),
        R.times(makeCourseRunEnrollment)
      )(2)
      // Set a couple start and end dates to create a range
      const twoDaysAgo = moment(now).add(-2, "days")
      const twoDaysFromNow = moment(now).add(2, "days")
      programRunEnrollments[1].run.start_date = twoDaysAgo.toISOString()
      programRunEnrollments[0].run.end_date = twoDaysFromNow.toISOString()
      const programEnrollment = makeProgramEnrollment()
      programEnrollment.course_run_enrollments = programRunEnrollments

      const dateRange = coursesApi.programDateRange(programEnrollment)
      assert.lengthOf(dateRange, 2)
      assert.equal(dateRange[0].toISOString(), twoDaysAgo.toISOString())
      assert.equal(dateRange[1].toISOString(), twoDaysFromNow.toISOString())
    })
  })

  describe("getDateSummary", () => {
    let courseRunEnrollment
    const now = moment()
    const past = moment(now).add(-1, "day")
    const future = moment(now).add(1, "day")

    beforeEach(() => {
      courseRunEnrollment = makeCourseRunEnrollment()
    })

    it("returns a summary if the start date is in the future", () => {
      courseRunEnrollment.run.start_date = future.toISOString()
      assert.deepEqual(coursesApi.getDateSummary(courseRunEnrollment), {
        text:       `Starts: ${formatPrettyDateTimeAmPm(future)}`,
        inProgress: false
      })
    })

    it("returns a summary with a past start date and future end date", () => {
      courseRunEnrollment.run.start_date = past.toISOString()
      courseRunEnrollment.run.end_date = future.toISOString()
      assert.deepEqual(coursesApi.getDateSummary(courseRunEnrollment), {
        text:       `Ends: ${formatPrettyDateTimeAmPm(future)}`,
        inProgress: true
      })
    })

    it("returns a summary with a past start date and null end date", () => {
      courseRunEnrollment.run.start_date = past.toISOString()
      courseRunEnrollment.run.end_date = null
      assert.deepEqual(coursesApi.getDateSummary(courseRunEnrollment), {
        text:       `Started: ${formatPrettyDate(past)}`,
        inProgress: true
      })
    })

    it("returns a summary with null start and end dates", () => {
      courseRunEnrollment.run.start_date = null
      courseRunEnrollment.run.end_date = null
      assert.deepEqual(coursesApi.getDateSummary(courseRunEnrollment), {
        text:       "Start and end dates pending",
        inProgress: false
      })
    })
  })
})
