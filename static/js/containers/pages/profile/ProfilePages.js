// @flow
import React from "react";
import { Routes, Route } from "react-router-dom";

import { routes } from "../../../lib/urls";

import ViewProfilePage from "./ViewProfilePage";
import EditProfilePage from "./EditProfilePage";

const ProfilePages = () => (
  <Routes>
    <Route exact path={routes.profile.view} component={ViewProfilePage} />
    <Route exact path={routes.profile.edit} component={EditProfilePage} />
  </Routes>
);

export default ProfilePages;
