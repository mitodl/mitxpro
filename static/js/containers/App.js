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
import { addUserNotification } from "../actions"
import { ALERT_TYPE_UNUSED_COUPON } from "../constants"

import Header from "../components/Header"
import PrivateRoute from "../components/PrivateRoute"

import CheckoutPage from "./pages/CheckoutPage"
import DashboardPage from "./pages/DashboardPage"
import ReceiptPage from "./pages/ReceiptPage"
import LoginPages from "./pages/login/LoginPages"
import RegisterPages from "./pages/register/RegisterPages"
import EcommerceAdminPages from "./pages/admin/EcommerceAdminPages"
import EcommerceBulkPages from "./pages/b2b/EcommerceBulkPages"
import ProfilePages from "./pages/profile/ProfilePages"
import AccountSettingsPage from "./pages/settings/AccountSettingsPage"
import EmailConfirmPage from "./pages/settings/EmailConfirmPage"

import type { Match, Location } from "react-router"
import type { CurrentUser } from "../flow/authTypes"

type Props = {
  match: Match,
  location: Location,
  currentUser: ?CurrentUser,
  addUserNotification: Function
}

export class App extends React.Component<Props, void> {
  componentDidUpdate(prevProps: Props) {
    if (this.shouldShowUnusedCouponAlert(prevProps, this.props)) {
      const { currentUser, addUserNotification } = this.props
      // $FlowFixMe: currentUser cannot be undefined or is_anonymous=true
      const unusedCoupon = currentUser.unused_coupons[0]
      addUserNotification({
        "unused-coupon": {
          type:  ALERT_TYPE_UNUSED_COUPON,
          props: {
            productId:  unusedCoupon.product_id,
            couponCode: unusedCoupon.coupon_code
          }
        }
      })
    }
  }

  shouldShowUnusedCouponAlert = (prevProps: Props, props: Props): ?boolean =>
    props.currentUser &&
    !props.currentUser.is_anonymous &&
    props.currentUser.unused_coupons.length > 0 &&
    // The user has just been loaded and the user is not currently on the checkout page
    ((!prevProps.currentUser && props.location.pathname !== routes.checkout) ||
      // The user just changed from the checkout page to another page
      (prevProps.location.pathname !== props.location.pathname &&
        prevProps.location.pathname === routes.checkout))

  render() {
    const { match, currentUser, location } = this.props

    if (!currentUser) {
      // application is still loading
      return <div className="app" />
    }

    return (
      <div className="app">
        <Header currentUser={currentUser} location={location} />
        <Switch>
          <PrivateRoute
            exact
            path={urljoin(match.url, routes.dashboard)}
            component={DashboardPage}
          />
          <PrivateRoute
            path={urljoin(match.url, routes.receipt)}
            component={ReceiptPage}
          />
          <Route
            path={urljoin(match.url, String(routes.login))}
            component={LoginPages}
          />
          <Route
            path={urljoin(match.url, String(routes.register))}
            component={RegisterPages}
          />
          <PrivateRoute
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
          <Route
            path={urljoin(match.url, String(routes.ecommerceBulk))}
            component={EcommerceBulkPages}
          />
          <PrivateRoute
            path={urljoin(match.url, String(routes.accountSettings))}
            component={AccountSettingsPage}
          />
          <Route
            path={urljoin(match.url, String(routes.account.confirmEmail))}
            component={EmailConfirmPage}
          />
        </Switch>
      </div>
    )
  }
}

const mapStateToProps = createStructuredSelector({
  currentUser: currentUserSelector
})

const mapDispatchToProps = {
  addUserNotification
}

const mapPropsToConfig = () => [users.currentUserQuery()]

export default compose(
  connect(
    mapStateToProps,
    mapDispatchToProps
  ),
  connectRequest(mapPropsToConfig)
)(App)
