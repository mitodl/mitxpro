// @flow
import React from "react"
import { Switch, Route, Redirect } from "react-router-dom"

import { routes } from "../../../lib/urls"

import RegisterEmailPage from "./RegisterEmailPage"
import RegisterConfirmPage from "./RegisterConfirmPage"
import RegisterProfilePage from "./RegisterProfilePage"

const RegisterPages = () => (
  <Switch>
    <Route exact path={routes.register.begin} component={RegisterEmailPage} />
    <Route
      exact
      path={routes.register.confirm}
      component={RegisterConfirmPage}
    />
    <Route
      exact
      path={routes.register.profile}
      component={RegisterProfilePage}
    />
    <Redirect to={routes.register.begin} />
  </Switch>
)

export default RegisterPages
