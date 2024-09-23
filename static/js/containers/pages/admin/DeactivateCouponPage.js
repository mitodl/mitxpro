// @flow
/* global SETTINGS: false */
import React from "react";
import DocumentTitle from "react-document-title";
import { DELETE_COUPONS_PAGE_TITLE } from "../../../constants";
import { mergeAll } from "ramda";
import { mutateAsync } from "redux-query";
import { compose } from "redux";
import { connect } from "react-redux";
import { Link } from "react-router-dom";

import { CouponDeactivateForm } from "../../../components/forms/CouponDeactivateForm";
import queries from "../../../lib/queries";
import { routes } from "../../../lib/urls";

import type { Response } from "redux-query";
import { createStructuredSelector } from "reselect";

type State = {
  deactivated: ?boolean,
};

type DispatchProps = {|
  deactivateCoupon: (coupon: Object) => Promise<Response<any>>,
|};

type Props = {|
  ...DispatchProps,
|};

export class DeactivateCouponPage extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      deactivated: false,
    };
  }

  onSubmit = async (
    couponData: Object,
    { setSubmitting, setErrors }: Object,
  ) => {
    const { deactivateCoupon } = this.props;
    try {
      const result = await deactivateCoupon(couponData);
      if (result.body && result.body.errors) {
        setErrors(mergeAll(result.body.errors));
      }
      await this.setState({ deactivated: true });
    } finally {
      setSubmitting(false);
    }
  };

  clearSuccess = async () => {
    await this.setState({ deactivated: false });
  };

  render() {
    const { deactivated } = this.state;
    return (
      <DocumentTitle
        title={`${SETTINGS.site_name} | ${DELETE_COUPONS_PAGE_TITLE}`}
      >
        <div className="ecommerce-admin-body">
          <p>
            <Link to={routes.ecommerceAdmin.index}>
              Back to Ecommerce Admin
            </Link>
          </p>
          <h3>Deactivate Coupons</h3>
          {deactivated ? (
            <div className="coupon-success-div">
              {<span>{`Coupon(s) successfully deactivated.`}</span>}
              <div>
                <input
                  type="button"
                  value="Deactivate more coupons"
                  onClick={this.clearSuccess}
                />
              </div>
            </div>
          ) : (
            <CouponDeactivateForm onSubmit={this.onSubmit} />
          )}
        </div>
      </DocumentTitle>
    );
  }
}

const deactivateCoupon = (coupon: Object) =>
  mutateAsync(queries.ecommerce.couponsDeactivation(coupon));

const mapStateToProps = createStructuredSelector({});

const mapDispatchToProps = {
  deactivateCoupon: deactivateCoupon,
};

export default compose(
  connect<Props, _, _, DispatchProps, _, _>(
    mapStateToProps,
    mapDispatchToProps,
  ),
)(DeactivateCouponPage);
