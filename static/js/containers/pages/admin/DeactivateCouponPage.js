// @flow
/* global SETTINGS: false */
import React from "react";
import DocumentTitle from "react-document-title";
import { DEACTIVATE_COUPONS_PAGE_TITLE } from "../../../constants";
import { mutateAsync } from "redux-query";
import { compose } from "redux";
import { connect } from "react-redux";
import { Link } from "react-router-dom";

import { CouponDeactivateForm } from "../../../components/forms/CouponDeactivateForm";
import queries from "../../../lib/queries";
import { routes } from "../../../lib/urls";

import type { Response } from "redux-query";
import { createStructuredSelector } from "reselect";
import ConfirmUpdateModal from "../../../components/ConfirmUpdateModal";
type State = {
  submitting: ?boolean,
  isDeactivated: ?boolean,
  openConfirmModal: ?boolean,
  couponData: Object,
  skippedCodes: Array<string>,
  numOfCouponsDeactivated: number,
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
      submitting: false,
      isDeactivated: false,
      openConfirmModal: false,
      couponData: {},
      skippedCodes: [],
      numOfCouponsDeactivated: 0,
    };
  }

  toggleOpenConfirmModal = async () => {
    await this.setState({
      ...this.state,
      openConfirmModal: !this.state.openConfirmModal,
    });
  };

  onModalSubmit = async () => {
    await this.setState({ ...this.state, submitting: true });
    const { deactivateCoupon } = this.props;
    const { couponData } = this.state;
    const result = await deactivateCoupon(couponData);

    await this.setState({
      submitting: false,
      couponData: couponData,
      openConfirmModal: false,
      isDeactivated: true,
      skippedCodes: result.body.skipped_codes || [],
      numOfCouponsDeactivated: result.body.num_of_coupons_deactivated,
    });
  };

  onSubmit = async (couponData: Object, { setSubmitting }: Object) => {
    await this.setState({ ...this.state, couponData: couponData });
    await this.toggleOpenConfirmModal();
    setSubmitting(false);
  };

  clearSuccess = async () => {
    await this.setState({
      submitting: false,
      isDeactivated: false,
      openConfirmModal: false,
      couponData: {},
      skippedCodes: [],
      numOfCouponsDeactivated: 0,
    });
  };

  render() {
    const {
      isDeactivated,
      openConfirmModal,
      skippedCodes,
      numOfCouponsDeactivated,
    } = this.state;
    return (
      <DocumentTitle
        title={`${SETTINGS.site_name} | ${DEACTIVATE_COUPONS_PAGE_TITLE}`}
      >
        <div className="ecommerce-admin-body">
          <ConfirmUpdateModal
            isOpen={openConfirmModal}
            toggle={this.toggleOpenConfirmModal}
            onConfirm={this.onModalSubmit}
            submitting={this.state.submitting}
            headerMessage="Confirm Coupon Deactivation"
            bodyText="Are you sure you want to deactivate coupon(s)?"
          />
          <p>
            <Link to={routes.ecommerceAdmin.index}>
              Back to Ecommerce Admin
            </Link>
          </p>
          <h3>Deactivate Coupon(s)</h3>
          {isDeactivated ? (
            <div className="coupon-success-div">
              {numOfCouponsDeactivated > 0 && (
                <div className="form-message form-success">
                  <p className="message-text">
                    Coupon(s) successfully deactivated.
                  </p>
                </div>
              )}
              {skippedCodes.length > 0 && (
                <div className="form-message form-warning">
                  <div className="message-div">
                    <p className="message-icon">⚠️</p>
                    <p className="message-text">
                      WARNING: The following coupon code(s) are incorrect.
                    </p>
                  </div>
                  <ul className="message-list">
                    {skippedCodes.map((code) => (
                      <li key={code}>{code}</li>
                    ))}
                  </ul>
                </div>
              )}
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
