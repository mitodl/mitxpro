// @flow
import React from "react"
import { Switch, Route, Redirect } from "react-router-dom"

import { routes } from "../../../lib/urls"

import RegisterEmailPage from "./RegisterEmailPage"
import RegisterConfirmPage from "./RegisterConfirmPage"
import RegisterConfirmSentPage from "./RegisterConfirmSentPage"
import RegisterDetailsPage from "./RegisterDetailsPage"
import RegisterExtraDetailsPage from "./RegisterExtraDetailsPage"
import RegisterDeniedPage from "./RegisterDeniedPage"
import RegisterErrorPage from "./RegisterErrorPage"

const RegisterPages = () => (
  <React.Fragment>
    <Switch>
      <Route exact path={routes.register.begin} component={RegisterEmailPage} />
      <Route
        exact
        path={routes.register.confirmSent}
        component={RegisterConfirmSentPage}
      />
      <Route
        exact
        path={routes.register.confirm}
        component={RegisterConfirmPage}
      />
      <Route
        exact
        path={routes.register.extra}
        component={RegisterExtraDetailsPage}
      />
      <Route
        exact
        path={routes.register.details}
        component={RegisterDetailsPage}
      />
      <Route exact path={routes.register.error} component={RegisterErrorPage} />
      <Route
        exact
        path={routes.register.denied}
        component={RegisterDeniedPage}
      />
      <Redirect to={routes.register.begin} />
    </Switch>
  </React.Fragment>
)

export default RegisterPages
