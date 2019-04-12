// @flow
import React from "react"
import { Switch, Route, Redirect } from "react-router-dom"

import { routes } from "../../../lib/urls"

import RegisterEmailPage from "./RegisterEmailPage"
import RegisterConfirmPage from "./RegisterConfirmPage"
import RegisterDetailsPage from "./RegisterDetailsPage"

const RegisterPages = () => (
  <React.Fragment>
    <h3>Register</h3>
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
        component={RegisterDetailsPage}
      />
      <Redirect to={routes.register.begin} />
    </Switch>
  </React.Fragment>
)

export default RegisterPages
