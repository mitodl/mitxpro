/* global SETTINGS: false */
// @flow
import { assert } from "chai"
import sinon from "sinon"
// $FlowFixMe: flow doesn't see fn
import moment, { fn as momentProto } from "moment"
import { mergeDeepRight } from "ramda"

import DashboardPage, {
  DashboardPage as InnerDashboardPage
} from "./DashboardPage"
import { formatPrettyDate } from "../../lib/util"
import { shouldIf } from "../../lib/test_utils"
import IntegrationTestHelper from "../../util/integration_test_helper"
import {
  makeCourseRunEnrollment,
  makeUserEnrollments
} from "../../factories/course"
import * as coursesApi from "../../lib/courses"
import * as utilFuncs from "../../lib/util"

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
      {
        location: {
          search: ""
        }
      }
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

  it("shows a message if the user has no enrollments", async () => {
    const { inner } = await renderPage({
      entities: {
        enrollments: {
          program_enrollments:    [],
          course_run_enrollments: []
        }
      }
    })

    const header = inner.find(".user-dashboard .header")
    assert.isTrue(header.exists())
    assert.include(
      header.text(),
      "You are not yet enrolled in any courses or programs"
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

  //
  ;[
    [
      moment()
        .add(-5, "days")
        .format(),
      "abc",
      true,
      "past start date, non-null courseware id"
    ],
    [
      moment()
        .add(-5, "days")
        .format(),
      null,
      false,
      "null courseware_url"
    ],
    [
      moment()
        .add(5, "days")
        .format(),
      "abc",
      false,
      "future start date"
    ],
    [null, "abc", false, "null start date"]
  ].forEach(([startDate, coursewareUrl, shouldLink, runDescription]) => {
    it(`${shouldIf(
      shouldLink
    )} link to edX if course run has ${runDescription}`, async () => {
      const userRunEnrollment = mergeDeepRight(makeCourseRunEnrollment(), {
        run: {
          courseware_url: coursewareUrl,
          start_date:     startDate
        }
      })
      const { inner } = await renderPage({
        entities: {
          enrollments: {
            program_enrollments:    [],
            course_run_enrollments: [userRunEnrollment]
          }
        }
      })

      const courseRunLink = inner.find(".course-enrollment h2 a")
      assert.equal(courseRunLink.exists(), shouldLink)
      if (shouldLink) {
        assert.include(
          courseRunLink.at(0).text(),
          userRunEnrollment.run.course.title
        )
      }
    })
  })

  describe("cybersource redirect", () => {
    it("shows an alert based on the toastMessage state value", async () => {
      const { inner } = await renderPage()
      assert.isFalse(inner.find("Alert").prop("isOpen"))
      inner.setState({ toastMessage: "hello world" })
      assert.isTrue(inner.find("Alert").prop("isOpen"))
      assert.isTrue(
        inner
          .find("Alert")
          .html()
          .includes("hello world")
      )
      inner.find("Alert").prop("toggle")()
      assert.isFalse(inner.find("Alert").prop("isOpen"))
      assert.equal(inner.state().toastMessage, "")
    })

    it("looks up a run or program using the query parameter, and displays the success message", async () => {
      const program = userEnrollments.program_enrollments[0].program
      const waitStub = helper.sandbox.stub(utilFuncs, "wait")
      const stub = helper.sandbox
        .stub(utilFuncs, "findItemWithReadableId")
        .returns(program)
      const { inner } = await renderPage(
        {},
        {
          location: {
            search: "readable_id=a+b+c&status=receipt"
          }
        }
      )
      assert.equal(
        inner.state().toastMessage,
        `You are now enrolled in ${program.title}!`
      )
      sinon.assert.calledWith(stub, userEnrollments, "a b c")
      assert.equal(waitStub.callCount, 0)
    })

    //
    ;[true, false].forEach(outOfTime => {
      it(`if a run or program is not immediately found it waits 3 seconds and ${
        outOfTime ? "errors" : "force reloads"
      }`, async () => {
        let waitResolve = null
        const waitPromise = new Promise(resolve => {
          waitResolve = resolve
        })
        const waitStub = helper.sandbox
          .stub(utilFuncs, "wait")
          .returns(waitPromise)
        const run = userEnrollments.course_run_enrollments[0].run
        const findStub = helper.sandbox
          .stub(utilFuncs, "findItemWithReadableId")
          .returns(null)

        const { inner } = await renderPage(
          {},
          {
            location: {
              search: "readable_id=xyz&status=receipt"
            }
          }
        )
        helper.handleRequestStub.resetHistory()

        sinon.assert.calledWith(waitStub, 3000)
        helper.sandbox.stub(momentProto, "isBefore").returns(!outOfTime)
        findStub.returns(run)
        // $FlowFixMe
        waitResolve()
        await waitPromise

        if (outOfTime) {
          assert.equal(
            inner.state().toastMessage,
            `Something went wrong. Please contact support at ${
              SETTINGS.support_email
            }.`
          )
        } else {
          sinon.assert.calledWith(
            helper.handleRequestStub,
            "/api/enrollments/",
            "GET"
          )
        }
      })
    })
  })
})
