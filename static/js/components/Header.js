// @flow
import React from "react"

import TopAppBar from "./TopAppBar"
import NotificationContainer from "./NotificationContainer"

import type { CurrentUser } from "../flow/authTypes"

type Props = {
  currentUser: CurrentUser
}

const Header = ({ currentUser }: Props) => (
  <React.Fragment>
    <TopAppBar currentUser={currentUser} />
    <NotificationContainer />
  </React.Fragment>
)

export default Header
