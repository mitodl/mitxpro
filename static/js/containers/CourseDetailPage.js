// @flow
import React from "react"
import R from "ramda"
import { connect } from "react-redux"
import {
  connectRequest,
  querySelectors,
} from "redux-query"
import { Link } from "react-router-dom"

import { courseRequest } from "../lib/api"
import { updateCourse } from "../actions"

class CourseDetailPage extends React.Component<*, void> {
  state = {
    titleEdit: ""
  }

  onTitleEditChange = (e) => {
    this.setState({
      titleEdit: e.target.value,
    });
  }

  onSubmit = () => {
    const { titleEdit } = this.state
    if (titleEdit === "") {
      return
    }
    this.props.updateCourse(
      this.props.course.id,
      {title: this.state.titleEdit}
    )
  }

  render() {
    const { isLoading, course } = this.props

    return (
      <div>
        <Link to={"/"}>back</Link><br />
        {isLoading && <div><em>Loading...</em></div>}
        {course && (
          <div>
            <div>Title: {course.title}</div>
            <div>
              New title: <input type="text" value={this.state.titleEdit} onChange={this.onTitleEditChange} />
            </div>
            <div><button onClick={this.onSubmit}>Submit Change</button></div>
          </div>
        )}
      </div>
    )
  }
}

const mapStateToProps = (state, ownProps) => {
  const courseQuery = courseRequest(ownProps.match.params.courseId)
  return {
    isLoading: querySelectors.isPending(state.queries, courseQuery),
    course:    state.entities.course,
    query:     courseQuery
  }
}

const mapPropsToConfigs = (props) => props.query

const mapDispatchToProps = (dispatch) => {
  return {
    updateCourse: (courseId, payload) => {
      dispatch(updateCourse(courseId, payload))
    },
  }
}

export default R.compose(
  connect(mapStateToProps, mapDispatchToProps),
  connectRequest(mapPropsToConfigs)
)(CourseDetailPage)
