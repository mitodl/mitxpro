// @flow
import React from "react";
import { Routes, Route } from "react-router-dom";

import { routes } from "../../../lib/urls";

import ViewProfilePage from "./ViewProfilePage";
import EditProfilePage from "./EditProfilePage";

const ProfilePages = () => (
  <Routes>
    <Route exact path={routes.profile.view} element={<ViewProfilePage />} />
    <Route exact path={routes.profile.edit} element={<EditProfilePage />} />
  </Routes>
);

export default ProfilePages;
