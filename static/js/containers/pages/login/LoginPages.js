// @flow
import React from "react";
import { Routes, Route } from "react-router-dom";

import { routes } from "../../../lib/urls";

import LoginEmailPage from "./LoginEmailPage";
import LoginPasswordPage from "./LoginPasswordPage";
import LoginForgotPasswordPage from "./LoginForgotPasswordPage";
import LoginForgotPasswordConfirmPage from "./LoginForgotPasswordConfirmPage";

function getForgotPasswordRoutes() {
  return [
    <Route
      key="forgot-begin"
      path={routes.login.forgot.begin}
      element={<LoginForgotPasswordPage />}
    />,
    <Route
      key="forgot-confirm"
      path={routes.login.forgot.confirm}
      element={<LoginForgotPasswordConfirmPage />}
    />,
  ];
}

const LoginPages = () => (
  <Routes>
    <Route path={routes.login.begin} element={<LoginEmailPage />} />
    <Route path={routes.login.password} element={<LoginPasswordPage />} />
    {getForgotPasswordRoutes()}
  </Routes>
);

export default LoginPages;
