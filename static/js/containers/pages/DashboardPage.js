// @flow
import React from "react"
import { compose } from "redux"
import { connect } from "react-redux"
import { connectRequest } from "redux-query"
import { createStructuredSelector } from "reselect"
import * as R from "ramda"
import { Collapse, Button } from "reactstrap"

import { RibbonText } from "../../components/Ribbon"
import queries from "../../lib/queries"
import { getDateSummary, programDateRange } from "../../lib/courses"
import { formatPrettyDate } from "../../lib/util"

import type {
  ProgramEnrollment,
  CourseRunEnrollment,
  UserEnrollments
} from "../../flow/courseTypes"

type Props = {
  enrollments: UserEnrollments
}

type State = {
  collapseVisible: Object
}

export class DashboardPage extends React.Component<Props, State> {
  state = {
    collapseVisible: {}
  }

  enrollmentsExist = (): boolean => {
    const { enrollments } = this.props

    return (
      enrollments &&
      (enrollments.program_enrollments.length > 0 ||
        enrollments.course_run_enrollments.length > 0)
    )
  }

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
                  {courseRunEnrollment.run.courseware_url ? (
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

    const enrollmentsExist = this.enrollmentsExist()

    return (
      <div className="user-dashboard container-fluid">
        <div className="row">
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
