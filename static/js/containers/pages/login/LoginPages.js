// @flow
import React from "react"
import { Switch, Route } from "react-router-dom"

import { routes } from "../../../lib/urls"

import LoginEmailPage from "./LoginEmailPage"
import LoginPasswordPage from "./LoginPasswordPage"

const LoginPages = () => (
  <React.Fragment>
    <h3>Log In</h3>
    <Switch>
      <Route exact path={routes.login.begin} component={LoginEmailPage} />
      <Route exact path={routes.login.password} component={LoginPasswordPage} />
    </Switch>
  </React.Fragment>
)

export default LoginPages
