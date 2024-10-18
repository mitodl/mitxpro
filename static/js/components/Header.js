// @flow
/* global SETTINGS:false */
import React from "react";
import * as Sentry from "@sentry/browser";
import posthog from "posthog-js";

import TopAppBar from "./TopAppBar";
import NotificationContainer from "./NotificationContainer";

import type { CurrentUser } from "../flow/authTypes";
import type { Location } from "react-router";
import type { CourseTopic } from "../flow/courseTypes";

type Props = {
  currentUser: ?CurrentUser,
  location: ?Location,
  errorPageHeader: ?boolean,
  courseTopics: Array<CourseTopic>,
};

const Header = ({
  currentUser,
  location,
  errorPageHeader,
  courseTopics,
}: Props) => {
  if (currentUser && currentUser.is_authenticated) {
    Sentry.configureScope((scope) => {
      scope.setUser({
        id: currentUser.id,
        email: currentUser.email,
        username: currentUser.username,
        name: currentUser.name,
      });
    });
    posthog.identify(currentUser.id, {
      environment: SETTINGS.environment,
      user_id: currentUser.id,
    });
  } else {
    Sentry.configureScope((scope) => {
      scope.setUser(null);
    });
  }
  return (
    <React.Fragment>
      <TopAppBar
        currentUser={currentUser}
        location={location}
        errorPageHeader={errorPageHeader}
        courseTopics={courseTopics}
      />
      <NotificationContainer />
    </React.Fragment>
  );
};

export default Header;
