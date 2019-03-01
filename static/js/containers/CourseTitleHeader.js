// @flow
import React from "react"
import R from "ramda"
import { connect } from "react-redux"
import {
  connectRequest,
  querySelectors,
} from "redux-query"

import { coursesRequest } from "../lib/api"

class CourseTitleHeader extends React.Component<*, void> {
  render() {
    const { isLoading, courses } = this.props

    return (
      <div style={{
        backgroundColor: "lightblue",
        padding: "10px",
        margin: "0 0 10px",
        borderRadius: "5px"
      }}>
        {courses && (<strong>Course Titles: </strong>)}
        {
          !isLoading && courses && R.values(courses).map((course) => (
            course.title
          )).join(", ")
        }
      </div>
    )
  }
}

const mapStateToProps = state => {
  return {
    isLoading: querySelectors.isPending(state.queries, coursesRequest()),
    courses:   state.entities.courses,
  }
}

const mapPropsToConfigs = () => coursesRequest()

export default R.compose(
  connect(mapStateToProps),
  connectRequest(mapPropsToConfigs)
)(CourseTitleHeader)
