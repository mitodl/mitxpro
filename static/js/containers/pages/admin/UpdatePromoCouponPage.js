// @flow
/* global SETTINGS: false */
import React from "react";
import DocumentTitle from "react-document-title";
import {
  UPDATE_PROMO_COUPON_MODAL_BODY,
  UPDATE_PROMO_COUPON_MODAL_HEADER,
  UPDATE_PROMO_COUPON_PAGE_TITLE,
} from "../../../constants";
import { connectRequest, mutateAsync } from "redux-query";
import { compose } from "redux";
import { connect } from "react-redux";
import { Link } from "react-router-dom";

import queries from "../../../lib/queries";
import { routes } from "../../../lib/urls";

import type { Response } from "redux-query";
import type { QueryConfig } from "redux-query";

import { createStructuredSelector } from "reselect";
import { PromoCouponUpdateForm } from "../../../components/forms/PromoCouponUpdateForm";
import ConfirmUpdateModal from "../../../components/ConfirmUpdateModal";
import type { Product, PromoCoupon } from "../../../flow/ecommerceTypes";

type State = {
  couponData: Object,
  isUpdated: ?boolean,
  openConfirmModal: ?boolean,
  submitting: ?boolean,
  errorMsg: string,
  responseMsg: string,
};

type StateProps = {|
  products: Array<Product>,
  promoCoupons: Array<PromoCoupon>,
|};

type DispatchProps = {|
  updatePromoCoupon: (
    coupon: Object,
  ) => Promise<Response<CouponPaymentVersion>>,
|};

type ReduxQueryProps = {
  forceRequest: (config: QueryConfig) => void,
};

type Props = {|
  ...StateProps,
  ...DispatchProps,
  ...ReduxQueryProps,
|};

export class UpdatePromoCouponPage extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props);
    props.forceRequest(queries.ecommerce.promoCouponsQuery());
    this.state = {
      couponData: {},
      openConfirmModal: false,
      submitting: false,
      isUpdated: false,
      errorMsg: "",
      responseMsg: "",
    };
  }
  toggleOpenConfirmModal = async () => {
    await this.setState({
      ...this.state,
      openConfirmModal: !this.state.openConfirmModal,
    });
  };

  onModalSubmit = async () => {
    const { updatePromoCoupon } = this.props;
    const { couponData } = this.state;

    couponData.product_ids = couponData.products.map((product) => product.id);
    await this.setState({ ...this.state, submitting: true });

    const result = await updatePromoCoupon(couponData);

    this.setState({
      couponData: couponData,
      isUpdated: true,
      openConfirmModal: false,
      submitting: false,
      errorMsg: result.body.error,
      responseMsg: result.body.message,
    });
  };

  onSubmit = async (couponData: Object, { setSubmitting }: Object) => {
    await this.setState({ ...this.state, couponData: couponData });
    await this.toggleOpenConfirmModal();
    setSubmitting(false);
  };

  clearSuccess = async () => {
    await this.setState({
      isUpdated: false,
      openConfirmModal: false,
      couponData: {},
      errorMsg: "",
      responseMsg: "",
    });
  };

  render() {
    const { openConfirmModal, responseMsg, isUpdated, errorMsg } = this.state;
    const { products, promoCoupons } = this.props;

    return (
      <DocumentTitle
        title={`${SETTINGS.site_name} | ${UPDATE_PROMO_COUPON_PAGE_TITLE}`}
      >
        <div className="ecommerce-admin-body">
          <ConfirmUpdateModal
            isOpen={openConfirmModal}
            toggle={this.toggleOpenConfirmModal}
            onConfirm={this.onModalSubmit}
            submitting={this.state.submitting}
            headerMessage={UPDATE_PROMO_COUPON_MODAL_HEADER}
            bodyText={UPDATE_PROMO_COUPON_MODAL_BODY}
          />
          <p>
            <Link to={routes.ecommerceAdmin.index}>
              Back to Ecommerce Admin
            </Link>
          </p>
          <h3>Update Promo Coupon</h3>
          {isUpdated ? (
            <div className="coupon-result-div">
              {responseMsg ? (
                <div className="form-message form-success">
                  <p className="message-text">{responseMsg}</p>
                </div>
              ) : (
                <div className="form-message form-warning">
                  <p className="message-text">{errorMsg}</p>
                </div>
              )}
              <div>
                <input
                  type="button"
                  value="Update more Promo Coupons"
                  onClick={this.clearSuccess}
                />
              </div>
            </div>
          ) : (
            <PromoCouponUpdateForm
              onSubmit={this.onSubmit}
              promoCoupons={promoCoupons}
              products={products?.filter(
                (product) => product.is_private === false,
              )}
            />
          )}
        </div>
      </DocumentTitle>
    );
  }
}

const updatePromoCoupon = (coupon: Object) =>
  mutateAsync(queries.ecommerce.promoCouponUpdation(coupon));

const mapPropsToConfig = () => [
  queries.ecommerce.productsQuery(),
  queries.ecommerce.promoCouponsQuery(),
];

const mapStateToProps = createStructuredSelector({
  products: queries.ecommerce.productsSelector,
  promoCoupons: queries.ecommerce.promoCouponsSelector,
});

const mapDispatchToProps = {
  updatePromoCoupon: updatePromoCoupon,
};

export default compose(
  connect<Props, _, _, DispatchProps, _, _>(
    mapStateToProps,
    mapDispatchToProps,
  ),
  connectRequest(mapPropsToConfig),
)(UpdatePromoCouponPage);
