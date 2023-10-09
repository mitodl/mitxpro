// @flow
/* global SETTINGS: false */
import React from "react"
import DocumentTitle from "react-document-title"
import { compose } from "redux"
import { connect } from "react-redux"
import { connectRequest, requestAsync } from "redux-query"
import { createStructuredSelector } from "reselect"


import { addUserNotification } from "../../actions"
import queries from "../../lib/queries"
import users, { currentUserSelector } from "../../lib/queries/users"


export class BlogPage extends React.Component {

  render() {

    return (
      <React.Fragment>
        <DocumentTitle
          title={`${SETTINGS.site_name} | Blog`}
        >
          <div className="user-dashboard container">
            <div className="row">
              <div className="header col-12">
                <h1>The Curve: An online learning blog for professionals, from MIT</h1>
                <href>SUBSCRIBE</href>
              </div>
            </div>
            <div className="top-posts-heading">
              <p>Editor's Pick</p>
              <p>Top Most Recent Posts</p>
            </div>
            <div className="top-posts-container">
              <div className="featured-post">This is Left Div</div>
              <div className="posts-sidebar">This is Right Div</div>
            </div>
          </div>
        </DocumentTitle>
      </React.Fragment>
    )
  }
}

const mapStateToProps = createStructuredSelector({
  enrollments: queries.enrollment.enrollmentsSelector,
  currentUser: currentUserSelector
})

const mapPropsToConfigs = () => [
  queries.enrollment.enrollmentsQuery(),
  users.currentUserQuery()
]

const requestDigitalCredentials = (uuid: string, isCourse: boolean) =>
  requestAsync({
    ...queries.digitalCredentials.requestDigitalCredentials(uuid, isCourse),
    force: true
  })

const mapDispatchToProps = {
  requestDigitalCredentials,
  addUserNotification
}

export default compose(
  connect(
    mapStateToProps,
    mapDispatchToProps
  ),
  connectRequest(mapPropsToConfigs)
)(BlogPage)
