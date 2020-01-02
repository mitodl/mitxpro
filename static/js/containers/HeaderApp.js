// @flow
import React from "react"
import { compose } from "redux"
import { connect } from "react-redux"
import { connectRequest } from "redux-query"
import { createStructuredSelector } from "reselect"

import users, { currentUserSelector } from "../lib/queries/users"
import { addUserNotification } from "../actions"
import { ALERT_TYPE_UNUSED_COUPON } from "../constants"

import Header from "../components/Header"

import type { Store } from "redux"
import type { CurrentUser } from "../flow/authTypes"

type Props = {
  currentUser: ?CurrentUser,
  store: Store<*, *>,
  addUserNotification: Function
}

export class HeaderApp extends React.Component<Props, void> {
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
    !prevProps.currentUser &&
    props.currentUser &&
    !props.currentUser.is_anonymous &&
    props.currentUser.unused_coupons.length > 0

  render() {
    const { currentUser } = this.props

    if (!currentUser) {
      // application is still loading
      return <div />
    }

    return <Header currentUser={currentUser} location={null} />
  }
}

const mapStateToProps = createStructuredSelector({
  currentUser: currentUserSelector
})

const mapPropsToConfig = () => [users.currentUserQuery()]

const mapDispatchToProps = {
  addUserNotification
}

export default compose(
  connect(
    mapStateToProps,
    mapDispatchToProps
  ),
  connectRequest(mapPropsToConfig)
)(HeaderApp)
