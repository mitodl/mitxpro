// @flow
import React from "react"
import { Switch, Route } from "react-router-dom"

import { routes } from "../../../lib/urls"

import ViewProfilePage from "./ViewProfilePage"
import EditProfilePage from "./EditProfilePage"

const ProfilePages = () => (
  <Switch>
    <Route exact path={routes.profile.view} component={ViewProfilePage} />
    <Route exact path={routes.profile.edit} component={EditProfilePage} />
  </Switch>
)

export default ProfilePages
