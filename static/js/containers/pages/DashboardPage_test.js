/* global SETTINGS: false */
// @flow
import { assert } from "chai"
import sinon from "sinon"
// $FlowFixMe: flow doesn't see fn
import moment, { fn as momentProto } from "moment"
import { mergeDeepRight, mergeRight } from "ramda"

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

import { makeUser, makeUnusedCoupon } from "../../factories/user"

import * as coursesApi from "../../lib/courses"
import * as utilFuncs from "../../lib/util"

describe("DashboardPage", () => {
  let helper,
    renderPage,
    userEnrollments,
    programDateRangeStub,
    getDateSummaryStub,
    currentUser
  const past = moment().add(-1, "days"),
    future = moment().add(1, "days")

  beforeEach(() => {
    helper = new IntegrationTestHelper()
    userEnrollments = makeUserEnrollments()
    currentUser = mergeRight(makeUser(), {
      unused_coupons: [makeUnusedCoupon()]
    })
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
          enrollments: userEnrollments,
          currentUser: currentUser
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
    const pastProgramEnrollments = userEnrollments.past_program_enrollments
    const programRunEnrollments = userEnrollments.program_enrollments[0].course_run_enrollments.concat(
      userEnrollments.past_program_enrollments[0].course_run_enrollments
    )
    const nonProgramRunEnrollments = userEnrollments.course_run_enrollments.concat(
      userEnrollments.past_course_run_enrollments
    )
    assert.lengthOf(programEnrollments, 1)
    assert.lengthOf(programRunEnrollments, 4)
    assert.lengthOf(nonProgramRunEnrollments, 4)
    assert.lengthOf(
      inner.find(".program-enrollment"),
      programEnrollments.length + pastProgramEnrollments.length
    )
    assert.lengthOf(
      inner.find(".program-enrollments .course-enrollment"),
      programRunEnrollments.length
    )
    assert.lengthOf(
      inner.find(".non-program-course-enrollments .course-enrollment"),
      nonProgramRunEnrollments.length
    )
    assert.lengthOf(
      inner.find(".enrollment-code"),
      currentUser.unused_coupons.length
    )
  })

  it("shows a message if the user has no enrollments", async () => {
    const { inner } = await renderPage({
      entities: {
        enrollments: {
          program_enrollments:    [],
          course_run_enrollments: []
        },
        currentUser: {
          is_authenticated: false
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
        userEnrollments.past_program_enrollments[0].course_run_enrollments
          .length +
        userEnrollments.course_run_enrollments.length +
        userEnrollments.past_course_run_enrollments.length
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

  //
  ;[true, false].forEach(willExpand => {
    it(`${
      willExpand ? "expands" : "collapses"
    } a program courses section`, async () => {
      const programEnrollmentId = userEnrollments.program_enrollments[0].id
      const { inner } = await renderPage({
        entities: {
          enrollments: {
            program_enrollments:      userEnrollments.program_enrollments,
            past_program_enrollments: []
          }
        }
      })

      inner.setState({
        collapseVisible: {
          [programEnrollmentId]: !willExpand
        }
      })
      assert.equal(
        inner
          .find("#expand-control Button")
          .childAt(0)
          .text(),
        willExpand ? "View Courses" : "Close"
      )
      assert.equal(
        inner.find("#expand-control .material-icons").text(),
        willExpand ? "expand_more" : "expand_less"
      )

      const collapseToggleBtn = inner
        .find(".program-enrollment .collapse-toggle")
        .at(0)
      collapseToggleBtn.prop("onClick")({})
      assert.deepEqual(inner.state("collapseVisible"), {
        [programEnrollmentId]: willExpand
      })
    })
  })

  //
  ;[
    [
      moment()
        .add(-5, "days")
        .format(),
      moment()
        .add(5, "days")
        .format(),
      "abc",
      true,
      "past start date, non-null courseware id"
    ],
    [
      moment()
        .add(-5, "days")
        .format(),
      moment()
        .add(-3, "days")
        .format(),
      "abc",
      false,
      "past start date, past end date, non-null courseware id"
    ],
    [
      moment()
        .add(-5, "days")
        .format(),
      moment()
        .add(5, "days")
        .format(),
      null,
      false,
      "null courseware_url"
    ],
    [
      moment()
        .add(5, "days")
        .format(),
      moment()
        .add(10, "days")
        .format(),
      "abc",
      false,
      "future start date"
    ],
    [null, null, "abc", false, "null start date"]
  ].forEach(
    ([startDate, endDate, coursewareUrl, shouldLink, runDescription]) => {
      it(`${shouldIf(
        shouldLink
      )} link to edX if course run has ${runDescription}`, async () => {
        const userRunEnrollment = mergeDeepRight(makeCourseRunEnrollment(), {
          run: {
            courseware_url: coursewareUrl,
            start_date:     startDate,
            end_date:       endDate
          }
        })
        const { inner } = await renderPage({
          entities: {
            enrollments: {
              program_enrollments:         [],
              past_program_enrollments:    [],
              course_run_enrollments:      [userRunEnrollment],
              past_course_run_enrollments: []
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
    }
  )

  //
  ;[
    [
      moment()
        .add(-5, "days")
        .format(),
      moment()
        .add(-3, "days")
        .format(),
      moment()
        .add(2, "days")
        .format(),
      "courseware_url",
      true,
      "has link, has ended and not yet expired"
    ],
    [
      moment()
        .add(-10, "days")
        .format(),
      moment()
        .add(-5, "days")
        .format(),
      moment()
        .add(1, "days")
        .format(),
      null,
      false,
      "has null link, has ended and not yet expired"
    ],
    [
      moment()
        .add(-5, "days")
        .format(),
      moment()
        .add(-3, "days")
        .format(),
      moment()
        .add(-1, "days")
        .format(),
      "courseware_url",
      false,
      "has link, has ended and expired"
    ]
  ].forEach(
    ([
      startDate,
      endDate,
      expirationDate,
      coursewareUrl,
      shouldLink,
      runDescription
    ]) => {
      it(`${shouldIf(
        shouldLink
      )} render link to archived course if course run ${runDescription}`, async () => {
        const pastRunEnrollments = mergeDeepRight(makeCourseRunEnrollment(), {
          run: {
            courseware_url:  coursewareUrl,
            start_date:      startDate,
            end_date:        endDate,
            expiration_date: expirationDate
          }
        })
        // We need the actual method, not the stub for this test
        coursesApi.getDateSummary.restore()
        const { inner } = await renderPage({
          entities: {
            enrollments: {
              program_enrollments:         [],
              past_program_enrollments:    [],
              course_run_enrollments:      [],
              past_course_run_enrollments: [pastRunEnrollments]
            }
          }
        })

        const courseRunLink = inner.find(
          ".course-enrollment .course-detail-column .archived-course-link a"
        )
        assert.equal(courseRunLink.exists(), shouldLink)
        if (shouldLink) {
          assert.equal(courseRunLink.at(0).prop("href"), coursewareUrl)
          assert.include(courseRunLink.at(0).text(), "View Archived Course")
        }
      })
    }
  )

  describe("cybersource redirect", () => {
    it("looks up a run or program using the query parameter, and displays the success message", async () => {
      const program = userEnrollments.program_enrollments[0].program
      const waitStub = helper.sandbox.stub(utilFuncs, "wait")
      const stub = helper.sandbox
        .stub(utilFuncs, "findItemWithTextId")
        .returns(program)
      const { store } = await renderPage(
        {},
        {
          location: {
            search: "purchased=a+b+c&status=purchased"
          }
        }
      )
      assert.deepEqual(store.getState().ui.userNotifications, {
        "order-status": {
          type:  "text",
          props: {
            text: `You are now enrolled in ${program.title}!`
          }
        }
      })
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
          .stub(utilFuncs, "findItemWithTextId")
          .returns(null)

        const { store } = await renderPage(
          {},
          {
            location: {
              search: "purchased=xyz&status=purchased"
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
          assert.deepEqual(store.getState().ui.userNotifications, {
            "order-status": {
              color: "danger",
              type:  "text",
              props: {
                text: `Something went wrong. Please contact support at ${
                  SETTINGS.support_email
                }.`
              }
            }
          })
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
