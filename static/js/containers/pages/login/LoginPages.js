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
      element={<LoginForgotPasswordPage />}
    />
    <Route
      exact
      path={routes.login.forgot.confirm}
      element={<LoginForgotPasswordConfirmPage />}
    />
    <Route
      exact
      path={routes.login.forgot.password}
      element={<LoginForgotPasswordPage />}
    />
  </React.Fragment>
);

const LoginPages = () => (
  <Routes>
    <Route exact path={routes.login.begin} element={<LoginEmailPage />} />
    <Route exact path={routes.login.password} element={<LoginPasswordPage />} />
    <Route
      exact
      path={routes.login.forgot.begin}
      element={<ForgotPasswordPages />}
    />
  </Routes>
);

export default LoginPages;
