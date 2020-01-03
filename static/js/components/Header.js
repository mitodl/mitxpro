// @flow
import React from "react"
import * as Sentry from "@sentry/browser"

import TopAppBar from "./TopAppBar"
import NotificationContainer from "./NotificationContainer"

import type { CurrentUser } from "../flow/authTypes"
import type { Location } from "react-router"

type Props = {
  currentUser: CurrentUser,
  location: ?Location
}

const Header = ({ currentUser, location }: Props) => {
  if (currentUser && currentUser.is_authenticated) {
    Sentry.configureScope(scope => {
      scope.setUser({
        id:       currentUser.id,
        email:    currentUser.email,
        username: currentUser.username,
        name:     currentUser.name
      })
    })
  } else {
    Sentry.configureScope(scope => {
      scope.setUser(null)
    })
  }
  return (
    <React.Fragment>
      <TopAppBar currentUser={currentUser} location={location} />
      <NotificationContainer />
    </React.Fragment>
  )
}

export default Header
