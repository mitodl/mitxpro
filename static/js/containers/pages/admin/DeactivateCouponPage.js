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
import { Modal, ModalHeader, ModalBody } from "reactstrap";

type State = {
  submitting: ?boolean,
  isDeactivated: ?boolean,
  openConfirmModal: ?boolean,
  couponData: Object,
  skippedCodes: Array<string>,
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
    });
  };

  render() {
    const { isDeactivated, openConfirmModal, skippedCodes } = this.state;
    return (
      <DocumentTitle
        title={`${SETTINGS.site_name} | ${DEACTIVATE_COUPONS_PAGE_TITLE}`}
      >
        <div className="ecommerce-admin-body">
          <Modal isOpen={openConfirmModal} toggle={this.toggleOpenConfirmModal}>
            <ModalHeader toggle={this.toggleOpenConfirmModal}>
              Confirm Coupon Deactivation
            </ModalHeader>
            <ModalBody>
              <div> Are you sure you want to deactivate coupon(s)?</div>
              <div className="float-container">
                <button
                  className="btn btn-gradient-white-to-blue"
                  onClick={() => this.toggleOpenConfirmModal()}
                >
                  Cancel
                </button>
                <button
                  className="btn btn-gradient-red-to-blue"
                  onClick={() => this.onModalSubmit()}
                  disabled={this.state.submitting}
                >
                  Deactivate
                </button>
              </div>
            </ModalBody>
          </Modal>
          <p>
            <Link to={routes.ecommerceAdmin.index}>
              Back to Ecommerce Admin
            </Link>
          </p>
          <h3>Deactivate Coupon(s)</h3>
          {isDeactivated ? (
            <div className="coupon-success-div">
              <span>Coupon(s) successfully deactivated.</span>
              {skippedCodes.length > 0 && (
                <div>
                  <p
                    className={"error"}
                  >{`The following coupon(s) are either already deactivated or the code(s) are incorrect.`}</p>
                  <ul className={"error"}>
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
