// @flow
/* global SETTINGS: false */
import React from "react";
import DocumentTitle from "react-document-title";
import {
  DISCOUNT_TYPE_PERCENT_OFF,
  CREATE_COUPON_PAGE_TITLE,
} from "../../../constants";
import { mergeAll } from "ramda";
import { connectRequest, mutateAsync } from "redux-query";
import { compose } from "redux";
import { connect } from "react-redux";
import { Link } from "react-router-dom";

import { CouponDeactivateForm } from "../../../components/forms/CouponDeactivateForm";
import queries from "../../../lib/queries";
import { routes } from "../../../lib/urls";

import type { Response } from "redux-query";
import type {
  Company,
  CouponPaymentVersion,
  Product,
} from "../../../flow/ecommerceTypes";
import { createStructuredSelector } from "reselect";
import { COUPON_TYPE_SINGLE_USE } from "../../../constants";

type State = {
  deleted: ?Boolean,
};

type StateProps = {|
  coupons: Map<string, CouponPaymentVersion>,
|};

type DispatchProps = {|
  deleteCoupon: (coupon: Object) => Promise<Response<CouponPaymentVersion>>,
|};

type Props = {|
  ...StateProps,
  ...DispatchProps,
|};

export class DeactivateCouponPage extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      deleted: false,
    };
  }

  onSubmit = async (
    couponData: Object,
    { setSubmitting, setErrors }: Object,
  ) => {
    const { coupons, deleteCoupon } = this.props;
    console.log(coupons)
    try {
      const result = await deleteCoupon(couponData);
      if (result.body && result.body.errors) {
        setErrors(mergeAll(result.body.errors));
      }
      await this.setState({deleted: true})
    } finally {
      setSubmitting(false);
    }
  };

  clearSuccess = async () => {
    await this.setState({ deleted: false });
  };

  render() {
    const { deleted } = this.state;
    return (
      <DocumentTitle
        title={`${SETTINGS.site_name} | ${CREATE_COUPON_PAGE_TITLE}`}
      >
        <div className="ecommerce-admin-body">
          <p>
            <Link to={routes.ecommerceAdmin.index}>
              Back to Ecommerce Admin
            </Link>
          </p>
          <h3>Deactivate Coupons</h3>
          {deleted ? (
            <div className="coupon-success-div">
              {
                <span>{`Coupons successfully deleted.`}</span>
              }
              <div>
                <input
                  type="button"
                  value="Delete more coupons"
                  onClick={this.clearSuccess}
                />
              </div>
            </div>
          ) : (
            <CouponDeactivateForm
              onSubmit={this.onSubmit}
            />
          )}
        </div>
      </DocumentTitle>
    );
  }
}

const deleteCoupon = (coupon: Object) =>
  mutateAsync(queries.ecommerce.couponsDeletion(coupon));

const mapStateToProps = createStructuredSelector({
  coupons: queries.ecommerce.couponsSelector,
});

const mapDispatchToProps = {
  deleteCoupon: deleteCoupon,
};

export default compose(
  connect<Props, _, _, DispatchProps, _, _>(
    mapStateToProps,
    mapDispatchToProps,
  ),
  // connectRequest(mapPropsToConfig),
)(DeactivateCouponPage);
