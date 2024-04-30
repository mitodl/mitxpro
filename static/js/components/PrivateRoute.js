// @flow
import React, { type ComponentType } from "react";
import { Route, Redirect } from "react-router-dom";
import { connect } from "react-redux";
import { compose } from "redux";
import { createStructuredSelector } from "reselect";

import { generateLoginRedirectUrl } from "../lib/auth";
import { currentUserSelector } from "../lib/queries/users";

import type { CurrentUser } from "../flow/authTypes";

type PrivateRouteProps = {
  component: ComponentType<any>,
  currentUser: ?CurrentUser,
  [key: string]: any,
};

export const PrivateRoute = ({
  component: Component,
  currentUser,
  ...routeProps
}: PrivateRouteProps) => {
  return (
    <Route
      {...routeProps}
      render={(props) => {
        return currentUser && currentUser.is_authenticated ? (
          <Component {...props} />
        ) : (
          <Redirect to={generateLoginRedirectUrl()} />
        );
      }}
    />
  );
};

const mapStateToProps = createStructuredSelector({
  currentUser: currentUserSelector,
});

export default compose(connect(mapStateToProps))(PrivateRoute);
