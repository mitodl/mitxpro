/* global SETTINGS: false */
// @flow
import React from "react"
import { compose } from "redux"
import { connect } from "react-redux"
import { connectRequest } from "redux-query"
import { createStructuredSelector } from "reselect"
import moment from "moment"
import * as R from "ramda"
import { Alert, Collapse, Button } from "reactstrap"
import qs from "query-string"

import { RibbonText } from "../../components/Ribbon"
import queries from "../../lib/queries"
import { getDateSummary, programDateRange } from "../../lib/courses"
import { formatPrettyDate, findItemWithTextId, wait } from "../../lib/util"

import type Moment from "moment"
import type { Location, RouterHistory } from "react-router"
import type {
  ProgramEnrollment,
  CourseRunEnrollment,
  UserEnrollments
} from "../../flow/courseTypes"

type Props = {
  enrollments: UserEnrollments,
  forceRequest: () => Promise<*>,
  history: RouterHistory,
  location: Location
}

type State = {
  collapseVisible: Object,
  now: Moment,
  timeoutActive: boolean,
  toastMessage: string,
  alertType: string
}

const NUM_MINUTES_TO_POLL = 2
const NUM_MILLIS_PER_POLL = 3000

export class DashboardPage extends React.Component<Props, State> {
  state = {
    collapseVisible: {},
    now:             moment(),
    timeoutActive:   false,
    toastMessage:    "",
    alertType:       ""
  }

  componentDidMount() {
    this.handleOrderStatus()
  }

  componentDidUpdate(prevProps: Props) {
    // This is meant to be an identity check, not a deep equality check. This shows whether we received an update
    // for enrollments based on the forceReload
    if (prevProps.enrollments !== this.props.enrollments) {
      this.handleOrderStatus()
    }
  }

  handleOrderStatus = () => {
    const {
      enrollments,
      location: { search }
    } = this.props
    if (!enrollments) {
      // wait until we have access to the dashboard
      return
    }

    const query = qs.parse(search)
    if (query.status === "purchased") {
      this.handleOrderPending(query.purchased)
    }
  }

  handleOrderPending = async (readableId: ?string) => {
    const { enrollments, forceRequest, history } = this.props
    const { timeoutActive, now: initialTime } = this.state

    if (timeoutActive) {
      return
    }

    const item = findItemWithTextId(enrollments, readableId)
    if (item) {
      history.push("/dashboard/")
      this.setState({
        toastMessage: `You are now enrolled in ${item.title}!`,
        alertType:    "info"
      })
      return
    }

    this.setState({ timeoutActive: true })
    await wait(NUM_MILLIS_PER_POLL)
    this.setState({ timeoutActive: false })

    const deadline = moment(initialTime).add(NUM_MINUTES_TO_POLL, "minutes")
    const now = moment()
    if (now.isBefore(deadline)) {
      await forceRequest()
    } else {
      this.setState({
        toastMessage: `Something went wrong. Please contact support at ${
          SETTINGS.support_email
        }.`,
        alertType: "danger"
      })
    }
  }

  enrollmentsExist = (): boolean => {
    const { enrollments } = this.props

    return (
      enrollments &&
      (enrollments.program_enrollments.length > 0 ||
        enrollments.course_run_enrollments.length > 0)
    )
  }

  isLinkableCourseRun = ({ run }: CourseRunEnrollment): boolean =>
    !R.isNil(run.courseware_url) &&
    !R.isNil(run.start_date) &&
    moment(run.start_date).isBefore(this.state.now)

  onCollapseToggle = (programEnrollmentId: number): void => {
    this.setState({
      collapseVisible: {
        ...this.state.collapseVisible,
        [programEnrollmentId]: !this.state.collapseVisible[programEnrollmentId]
      }
    })
  }

  renderCourseEnrollment = R.curry(
    (
      isProgramCourse: boolean,
      courseRunEnrollment: CourseRunEnrollment,
      index: number
    ) => {
      const dateSummary = getDateSummary(courseRunEnrollment)

      return (
        <div className="course-enrollment row" key={index}>
          {!isProgramCourse && (
            <RibbonText text="Course" addedClasses="course" />
          )}
          <div className="course-image-column col-12 col-md-3">
            <img
              src={courseRunEnrollment.run.course.thumbnail_url}
              alt="Course image"
            />
          </div>
          <div className="course-detail-column col-12 col-md-9">
            <div className="row">
              <div className="col-12 col-md-9">
                <h2>
                  {this.isLinkableCourseRun(courseRunEnrollment) ? (
                    <a
                      href={courseRunEnrollment.run.courseware_url}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      {courseRunEnrollment.run.course.title}
                    </a>
                  ) : (
                    <span>{courseRunEnrollment.run.course.title}</span>
                  )}
                </h2>
              </div>
              <div className="status col-12 col-md-auto col-lg-3">
                {isProgramCourse && dateSummary.inProgress && (
                  <span>In Progress</span>
                )}
              </div>
              <div className="date-summary-text col-12">{dateSummary.text}</div>
            </div>
          </div>
        </div>
      )
    }
  )

  renderProgramEnrollment = (
    programEnrollment: ProgramEnrollment,
    index: number
  ) => {
    const { collapseVisible } = this.state

    const dateRange = programDateRange(programEnrollment)
    const isExpanded = collapseVisible[programEnrollment.id]

    return (
      <div className="program-enrollment row" key={index}>
        <RibbonText text="Program" addedClasses="program" />

        <div className="program-image-column col-12 col-md-3">
          <img
            src={programEnrollment.program.thumbnail_url}
            alt="Program image"
          />
        </div>
        <div className="program-detail-column col-12 col-md-9">
          <div className="row no-gutters">
            <div className="col-12 col-md-9">
              <h2>{programEnrollment.program.title}</h2>
              <section className="program-details">
                {dateRange[0] && dateRange[1] && (
                  <div>
                    {formatPrettyDate(dateRange[0])}
                    {" – "}
                    {formatPrettyDate(dateRange[1])}
                  </div>
                )}
                <div>
                  Courses – {programEnrollment.course_run_enrollments.length}
                </div>
              </section>
            </div>
          </div>

          <Collapse
            className="program-course"
            isOpen={collapseVisible[programEnrollment.id]}
          >
            <section className="program-courses">
              <hr />
              <h5>List of courses in this program:</h5>
              <div>
                {programEnrollment.course_run_enrollments.map(
                  this.renderCourseEnrollment(true)
                )}
              </div>
            </section>
          </Collapse>

          <div className="expand-control">
            <Button
              className={`collapse-toggle btn-link shadow-none ${isExpanded &&
                "expanded"}`}
              onClick={R.partial(this.onCollapseToggle, [programEnrollment.id])}
            >
              {isExpanded ? <span>Close</span> : <span>View Courses</span>}
            </Button>
          </div>
        </div>
      </div>
    )
  }

  render() {
    const { enrollments } = this.props
    const { alertType, toastMessage } = this.state

    const enrollmentsExist = this.enrollmentsExist()

    return (
      <React.Fragment>
        <div className="user-dashboard container">
          <div className="row">
            <Alert
              color={alertType}
              isOpen={!!toastMessage}
              toggle={() =>
                this.setState({
                  alertType:    "",
                  toastMessage: ""
                })
              }
            >
              {toastMessage}
            </Alert>
            <div className="header col-12">
              <h1>Dashboard</h1>
              {enrollments &&
                (enrollmentsExist ? (
                  <h3>Courses and Programs</h3>
                ) : (
                  <h2>You are not yet enrolled in any courses or programs.</h2>
                ))}
            </div>
          </div>
          {enrollments ? (
            <React.Fragment>
              <div className="program-enrollments">
                {enrollments.program_enrollments.map(
                  this.renderProgramEnrollment
                )}
              </div>
              <div className="non-program-course-enrollments">
                {enrollments.course_run_enrollments.map(
                  this.renderCourseEnrollment(false)
                )}
              </div>
            </React.Fragment>
          ) : (
            <span>Loading...</span>
          )}
        </div>
      </React.Fragment>
    )
  }
}

const mapStateToProps = createStructuredSelector({
  enrollments: queries.enrollment.enrollmentsSelector
})

const mapPropsToConfigs = () => [queries.enrollment.enrollmentsQuery()]

export default compose(
  connect(mapStateToProps),
  connectRequest(mapPropsToConfigs)
)(DashboardPage)
