// @flow
/* global SETTINGS: false */
import React from "react";
import { compose } from "redux";
import { connect } from "react-redux";
import { connectRequest } from "redux-query";
import { createStructuredSelector } from "reselect";

import users, { currentUserSelector } from "../lib/queries/users";
import catalog from "../lib/queries/catalog";
import { addUserNotification } from "../actions";
import { ALERT_TYPE_UNUSED_COUPON } from "../constants";

import Header from "../components/Header";

import type { Store } from "redux";
import type { CurrentUser } from "../flow/authTypes";
import type { CourseTopic } from "../flow/courseTypes";

type Props = {
  currentUser: ?CurrentUser,
  store: Store<*, *>,
  addUserNotification: Function,
  courseTopics: Array<CourseTopic>,
};

const errorPageHeader =
  document.getElementsByClassName("error-page-header").length > 0
    ? true
    : false;

export class HeaderApp extends React.Component<Props, void> {
  componentDidUpdate(prevProps: Props) {
    if (this.shouldShowUnusedCouponAlert(prevProps, this.props)) {
      const { currentUser, addUserNotification } = this.props;
      // $FlowFixMe: currentUser cannot be undefined or is_anonymous=true
      const unusedCoupon = currentUser.unused_coupons[0];
      addUserNotification({
        "unused-coupon": {
          type: ALERT_TYPE_UNUSED_COUPON,
          props: {
            productId: unusedCoupon.product_id,
            couponCode: unusedCoupon.coupon_code,
          },
        },
      });
    }
  }

  shouldShowUnusedCouponAlert = (prevProps: Props, props: Props): ?boolean =>
    !prevProps.currentUser &&
    props.currentUser &&
    !props.currentUser.is_anonymous &&
    props.currentUser.unused_coupons.length > 0;

  render() {
    const { currentUser, courseTopics } = this.props;

    if (!currentUser && !errorPageHeader && !courseTopics) {
      // application is still loading
      return <div />;
    }

    return (
      <Header
        currentUser={currentUser}
        location={null}
        errorPageHeader={errorPageHeader}
        courseTopics={courseTopics}
      />
    );
  }
}

const mapStateToProps = createStructuredSelector({
  currentUser: currentUserSelector,
  courseTopics: catalog.courseTopicsSelector,
});

const mapPropsToConfig = () =>
  errorPageHeader
    ? []
    : [users.currentUserQuery(), catalog.courseTopicsQuery()];

const mapDispatchToProps = {
  addUserNotification,
};

export default compose(
  connect(mapStateToProps, mapDispatchToProps),
  connectRequest(mapPropsToConfig),
)(HeaderApp);
