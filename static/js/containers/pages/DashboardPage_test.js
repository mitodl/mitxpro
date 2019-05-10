// @flow
import { assert } from "chai"
import sinon from "sinon"
import moment from "moment"

import DashboardPage, {
  DashboardPage as InnerDashboardPage
} from "./DashboardPage"
import { formatPrettyDate } from "../../lib/util"
import IntegrationTestHelper from "../../util/integration_test_helper"
import { makeUserEnrollments } from "../../factories/course"
import * as coursesApi from "../../lib/courses"

describe("DashboardPage", () => {
  let helper,
    renderPage,
    userEnrollments,
    programDateRangeStub,
    getDateSummaryStub
  const past = moment().add(-1, "days"),
    future = moment().add(1, "days")

  beforeEach(() => {
    helper = new IntegrationTestHelper()
    userEnrollments = makeUserEnrollments()
    programDateRangeStub = helper.sandbox
      .stub(coursesApi, "programDateRange")
      .returns([past, future])
    getDateSummaryStub = helper.sandbox
      .stub(coursesApi, "getDateSummary")
      .returns({ text: "Ends: January 1, 2019", inProgress: true })

    renderPage = helper.configureHOCRenderer(
      DashboardPage,
      InnerDashboardPage,
      {
        entities: {
          enrollments: userEnrollments
        }
      },
      {}
    )
  })

  afterEach(() => {
    helper.cleanup()
  })

  it("renders a dashboard", async () => {
    const { inner } = await renderPage()
    assert.isTrue(inner.find(".user-dashboard").exists())
    const programEnrollments = userEnrollments.program_enrollments
    const programRunEnrollments =
      userEnrollments.program_enrollments[0].course_run_enrollments
    const nonProgramRunEnrollments = userEnrollments.course_run_enrollments
    assert.lengthOf(programEnrollments, 1)
    assert.lengthOf(programRunEnrollments, 2)
    assert.lengthOf(nonProgramRunEnrollments, 2)
    assert.lengthOf(
      inner.find(".program-enrollment"),
      programEnrollments.length
    )
    assert.lengthOf(
      inner.find(".program-enrollments .course-enrollment"),
      programRunEnrollments.length
    )
    assert.lengthOf(
      inner.find(".non-program-course-enrollments .course-enrollment"),
      nonProgramRunEnrollments.length
    )
  })

  it("shows specific date information", async () => {
    const { inner } = await renderPage()
    sinon.assert.calledWith(
      programDateRangeStub,
      userEnrollments.program_enrollments[0]
    )
    sinon.assert.callCount(
      getDateSummaryStub,
      userEnrollments.program_enrollments[0].course_run_enrollments.length +
        userEnrollments.course_run_enrollments.length
    )

    const dates = programDateRangeStub()
    assert.include(
      inner
        .find(".program-details")
        .at(0)
        .text(),
      `${formatPrettyDate(dates[0])} – ${formatPrettyDate(dates[1])}`
    )

    const dateSummary = getDateSummaryStub()
    const courseEnrollmentEl = inner.find(".course-enrollment").at(0)
    assert.equal(courseEnrollmentEl.find(".status").text(), "In Progress")
    assert.equal(
      courseEnrollmentEl.find(".date-summary-text").text(),
      dateSummary.text
    )
  })

  it("expands and collapses a program courses section", async () => {
    const { inner } = await renderPage()
    const collapseToggleBtn = inner
      .find(".program-enrollment .collapse-toggle")
      .at(0)
    collapseToggleBtn.prop("onClick")({})
    inner.update()
    const programEnrollmentId = userEnrollments.program_enrollments[0].id
    assert.deepEqual(inner.state("collapseVisible"), {
      [programEnrollmentId]: true
    })
    collapseToggleBtn.prop("onClick")({})
    inner.update()
    assert.deepEqual(inner.state("collapseVisible"), {
      [programEnrollmentId]: false
    })
  })
})
