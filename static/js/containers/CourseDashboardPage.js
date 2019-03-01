// @flow
import React from "react"
import R from "ramda"
import { connect } from "react-redux"
import {
  connectRequest,
  querySelectors,
} from "redux-query"
import { Link } from "react-router-dom"

import { coursesRequest } from "../lib/api"
import { deleteCourse } from "../actions"

class CourseDashboardPage extends React.Component<*, void> {
  onDeleteClick = (courseId) => {
    this.props.deleteCourse(courseId)
  }

  render() {
    const { isLoading, courses } = this.props

    return (
      <div>
        <h2>Course Dashboard</h2>
        {isLoading && <div><em>Loading...</em></div>}
        {courses && R.values(courses).map((course, i) => (
          <div key={i} style={{paddingBottom: "10px"}}>
            <div>
              Course:&nbsp;
              <Link to={`/courses/${course.id}`}>{course.title}</Link>
            </div>
            <div>{course.description}</div>
            <button onClick={R.partial(this.onDeleteClick, [course.id])}>Delete</button>
          </div>
        ))}
      </div>
    )
  }
}

const mapStateToProps = state => {
  const query = coursesRequest()
  return {
    isLoading: querySelectors.isPending(state.queries, query),
    courses:   state.entities.courses,
    query:     query
  }
}

const mapDispatchToProps = (dispatch) => {
  return {
    deleteCourse: (courseId) => {
      dispatch(deleteCourse(courseId))
    },
  }
}

const mapPropsToConfigs = (props) => props.query

export default R.compose(
  connect(mapStateToProps, mapDispatchToProps),
  connectRequest(mapPropsToConfigs),
)(CourseDashboardPage)
