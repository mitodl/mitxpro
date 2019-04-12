// @flow
import React from "react"
import { compose } from "redux"
import { connect } from "react-redux"
import { connectRequest } from "redux-query"
import { createStructuredSelector } from "reselect"

import users, { currentUserSelector } from "../lib/queries/users"

import TopAppBar from "../components/TopAppBar"

import type { Store } from "redux"
import type { Match } from "react-router"
import type { CurrentUser } from "../flow/authTypes"

type Props = {
  match: Match,
  currentUser: ?CurrentUser,
  store: Store<*, *>
}

class HeaderApp extends React.Component<Props, void> {
  render() {
    const { currentUser } = this.props

    if (!currentUser) {
      // application is still loading
      return <div />
    }

    return <TopAppBar currentUser={currentUser} />
  }
}

const mapStateToProps = createStructuredSelector({
  currentUser: currentUserSelector
})

const mapPropsToConfig = () => [users.currentUserQuery()]

export default compose(
  connect(mapStateToProps),
  connectRequest(mapPropsToConfig)
)(HeaderApp)
