// @flow
import React from "react";
import { Routes, Route } from "react-router-dom";

import { routes } from "../../../lib/urls";

import LoginEmailPage from "./LoginEmailPage";
import LoginPasswordPage from "./LoginPasswordPage";
import LoginForgotPasswordPage from "./LoginForgotPasswordPage";
import LoginForgotPasswordConfirmPage from "./LoginForgotPasswordConfirmPage";

const ForgotPasswordPages = () => (
  <React.Fragment>
    <Route
      exact
      path={routes.login.forgot.begin}
      component={LoginForgotPasswordPage}
    />
    <Route
      exact
      path={routes.login.forgot.confirm}
      component={LoginForgotPasswordConfirmPage}
    />
  </React.Fragment>
);

const LoginPages = () => (
  <Routes>
    <Route exact path={routes.login.begin} component={LoginEmailPage} />
    <Route exact path={routes.login.password} component={LoginPasswordPage} />
    <Route
      path={routes.login.forgot.toString()}
      component={ForgotPasswordPages}
    />
  </Routes>
);

export default LoginPages;
