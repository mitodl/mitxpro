// @flow
import React from "react";
import { Routes, Route, Navigate } from "react-router-dom";

import { routes } from "../../../lib/urls";

import RegisterEmailPage from "./RegisterEmailPage";
import RegisterConfirmPage from "./RegisterConfirmPage";
import RegisterConfirmSentPage from "./RegisterConfirmSentPage";
import RegisterDetailsPage from "./RegisterDetailsPage";
import RegisterExtraDetailsPage from "./RegisterExtraDetailsPage";
import RegisterDeniedPage from "./RegisterDeniedPage";
import RegisterErrorPage from "./RegisterErrorPage";

const RegisterPages = () => (
  <React.Fragment>
    <Routes>
      <Route
        exact
        path={routes.register.begin}
        element={<RegisterEmailPage />}
      />
      <Route
        exact
        path={routes.register.confirmSent}
        element={<RegisterConfirmSentPage />}
      />
      <Route
        exact
        path={routes.register.confirm}
        element={<RegisterConfirmPage />}
      />
      <Route
        exact
        path={routes.register.extra}
        element={<RegisterExtraDetailsPage />}
      />
      <Route
        exact
        path={routes.register.details}
        element={<RegisterDetailsPage />}
      />
      <Route
        exact
        path={routes.register.error}
        element={<RegisterErrorPage />}
      />
      <Route
        exact
        path={routes.register.denied}
        element={<RegisterDeniedPage />}
      />
      <Navigate to={routes.register.begin} />
    </Routes>
  </React.Fragment>
);

export default RegisterPages;
