// @flow
/* global SETTINGS: false */
declare var dataLayer: Object[]
declare var CSOURCE_PAYLOAD: ?Object

import React from "react"
import DocumentTitle from "react-document-title"
import { DASHBOARD_PAGE_TITLE } from "../../constants"
import { compose } from "redux"
import { connect } from "react-redux"
import { connectRequest } from "redux-query"
import { createStructuredSelector } from "reselect"
import moment from "moment"
import * as R from "ramda"
import { Collapse, Button } from "reactstrap"
import qs from "query-string"

import { RibbonText } from "../../components/Ribbon"

import { addUserNotification } from "../../actions"
import queries from "../../lib/queries"
import { routes } from "../../lib/urls"
import { getDateSummary, programDateRange } from "../../lib/courses"
import { formatPrettyDate, findItemWithTextId, wait } from "../../lib/util"

import type Moment from "moment"
import type { Location, RouterHistory } from "react-router"
import type {
  ProgramEnrollment,
  CourseRunEnrollment,
  UserEnrollments
} from "../../flow/courseTypes"
import { ALERT_TYPE_TEXT } from "../../constants"

type Props = {
  addUserNotification: Function,
  enrollments: UserEnrollments,
  forceRequest: () => Promise<*>,
  history: RouterHistory,
  location: Location
}

type State = {
  collapseVisible: Object,
  now: Moment,
  timeoutActive: boolean
}

const NUM_MINUTES_TO_POLL = 2
const NUM_MILLIS_PER_POLL = 3000

export class DashboardPage extends React.Component<Props, State> {
  state = {
    collapseVisible: {},
    now:             moment(),
    timeoutActive:   false
  }

  componentDidMount() {
    if (CSOURCE_PAYLOAD && SETTINGS.gtmTrackingID) {
      dataLayer.push({
        event:            "purchase",
        transactionId:    CSOURCE_PAYLOAD.transaction_id,
        transactionTotal: CSOURCE_PAYLOAD.transaction_total,
        productType:      CSOURCE_PAYLOAD.product_type,
        coursewareId:     CSOURCE_PAYLOAD.courseware_id,
        referenceNumber:  CSOURCE_PAYLOAD.reference_number
      })
      CSOURCE_PAYLOAD = null
    }
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
    const {
      addUserNotification,
      enrollments,
      forceRequest,
      history
    } = this.props
    const { timeoutActive, now: initialTime } = this.state

    if (timeoutActive) {
      return
    }

    const item = findItemWithTextId(enrollments, readableId)
    if (item) {
      history.push("/dashboard/")

      addUserNotification({
        "order-status": {
          type:  ALERT_TYPE_TEXT,
          props: {
            text: `You are now enrolled in ${item.title}!`
          }
        }
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
      addUserNotification({
        "order-status": {
          type:  ALERT_TYPE_TEXT,
          color: "danger",
          props: {
            text: `Something went wrong. Please contact support at ${SETTINGS.support_email}.`
          }
        }
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

  pastEnrollmentsExist = (): boolean => {
    const { enrollments } = this.props

    return (
      enrollments &&
      (enrollments.past_program_enrollments.length > 0 ||
        enrollments.past_course_run_enrollments.length > 0)
    )
  }

  isLinkableCourseRun = ({ run }: CourseRunEnrollment): boolean =>
    !R.isNil(run.courseware_url) &&
    !R.isNil(run.start_date) &&
    moment(run.start_date).isBefore(this.state.now) &&
    (R.isNil(run.end_date) || moment(run.end_date).isAfter(this.state.now))

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
            <div className="row mt-2">
              <div className="archived-course-link col-lg-7 col-md-8">
                {dateSummary.archived &&
                courseRunEnrollment.run.courseware_url ? (
                    <a
                      href={courseRunEnrollment.run.courseware_url}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                    View Archived Course
                    </a>
                  ) : null}
              </div>
              <div className="certificate-link d-flex justify-content-lg-end col-lg-5 col-md-8">
                {courseRunEnrollment.certificate ? (
                  <a
                    href={courseRunEnrollment.certificate.link}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    View Certificate
                  </a>
                ) : null}
              </div>
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

        <div className="program-image-column col-lg-3 col-md-5">
          <img
            src={programEnrollment.program.thumbnail_url}
            alt="Program image"
          />
        </div>
        <div className="program-detail-column col-lg-9 col-md-7">
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
          <div className="row no-gutters mb-3">
            <div className="certificate-link d-flex justify-content-lg-end col-12">
              {programEnrollment.certificate ? (
                <a
                  href={programEnrollment.certificate.link}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  View Certificate
                </a>
              ) : null}
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
              className="collapse-toggle btn-link shadow-none"
              onClick={R.partial(this.onCollapseToggle, [programEnrollment.id])}
            >
              {isExpanded ? <span>Close</span> : <span>View Courses</span>}
              <i className="material-icons">
                {isExpanded ? "expand_less" : "expand_more"}
              </i>
            </Button>
          </div>
        </div>
      </div>
    )
  }

  render() {
    const { enrollments } = this.props

    const enrollmentsExist = this.enrollmentsExist()
    const pastEnrollmentsExist = this.pastEnrollmentsExist()

    return (
      <React.Fragment>
        <DocumentTitle
          title={`${SETTINGS.site_name} | ${DASHBOARD_PAGE_TITLE}`}
        >
          <div className="user-dashboard container">
            <div className="row">
              <div className="header col-12">
                <h1>Dashboard</h1>
                {enrollments &&
                  (enrollmentsExist ? (
                    <h3>Courses and Programs</h3>
                  ) : (
                    <div className="empty-msg">
                      <h2>
                        You are not yet enrolled in any courses or programs.
                      </h2>
                      <a
                        href={routes.catalog}
                        className="link-button light-blue"
                      >
                        Browse Our Catalog
                      </a>
                    </div>
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
                {pastEnrollmentsExist ? (
                  <div className="past-enrollments">
                    <h3>Past Courses and Programs</h3>
                    <div className="program-enrollments">
                      {enrollments.past_program_enrollments.map(
                        this.renderProgramEnrollment
                      )}
                    </div>
                    <div className="non-program-course-enrollments">
                      {enrollments.past_course_run_enrollments.map(
                        this.renderCourseEnrollment(false)
                      )}
                    </div>
                  </div>
                ) : null}
              </React.Fragment>
            ) : (
              <span>Loading...</span>
            )}
          </div>
        </DocumentTitle>
      </React.Fragment>
    )
  }
}

const mapStateToProps = createStructuredSelector({
  enrollments: queries.enrollment.enrollmentsSelector
})

const mapDispatchToProps = {
  addUserNotification
}

const mapPropsToConfigs = () => [queries.enrollment.enrollmentsQuery()]

export default compose(
  connect(
    mapStateToProps,
    mapDispatchToProps
  ),
  connectRequest(mapPropsToConfigs)
)(DashboardPage)
