// @flow
import React from "react"
import { compose } from "redux"
import { connect } from "react-redux"
import { Switch, Route } from "react-router"
import { connectRequest } from "redux-query"
import { createStructuredSelector } from "reselect"
import urljoin from "url-join"

import users, { currentUserSelector } from "../lib/queries/users"
import { routes } from "../lib/urls"

import TopAppBar from "../components/TopAppBar"
import PrivateRoute from "../components/PrivateRoute"
import NotificationContainer from "../components/NotificationContainer"

import CheckoutPage from "./pages/CheckoutPage"
import DashboardPage from "./pages/DashboardPage"
import LoginPages from "./pages/login/LoginPages"
import RegisterPages from "./pages/register/RegisterPages"
import EcommerceAdminPages from "./pages/admin/EcommerceAdminPages"

import type { Match } from "react-router"
import type { CurrentUser } from "../flow/authTypes"
import ProfilePages from "./pages/profile/ProfilePages"

type Props = {
  match: Match,
  currentUser: ?CurrentUser
}

class App extends React.Component<Props, void> {
  render() {
    const { match, currentUser } = this.props

    if (!currentUser) {
      // application is still loading
      return <div className="app" />
    }

    return (
      <div className="app">
        <TopAppBar currentUser={currentUser} />
        <NotificationContainer />
        <Switch>
          <PrivateRoute
            exact
            path={urljoin(match.url, routes.dashboard)}
            component={DashboardPage}
          />
          <Route
            path={urljoin(match.url, String(routes.login))}
            component={LoginPages}
          />
          <Route
            path={urljoin(match.url, String(routes.register))}
            component={RegisterPages}
          />
          <Route
            path={urljoin(match.url, routes.checkout)}
            component={CheckoutPage}
          />
          <Route
            path={urljoin(match.url, String(routes.ecommerceAdmin))}
            component={EcommerceAdminPages}
          />
          <Route
            path={urljoin(match.url, String(routes.profile))}
            component={ProfilePages}
          />
        </Switch>
      </div>
    )
  }
}

const mapStateToProps = createStructuredSelector({
  currentUser: currentUserSelector
})

const mapPropsToConfig = () => [users.currentUserQuery()]

export default compose(
  connect(mapStateToProps),
  connectRequest(mapPropsToConfig)
)(App)
