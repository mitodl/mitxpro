// @flow
/* global SETTINGS: false */
import React from "react";
import DocumentTitle from "react-document-title";
import { PROCESS_COUPON_ASSIGNMENT_SHEET_PAGE_TITLE } from "../../../constants";
import { mutateAsync } from "redux-query";
import { compose } from "redux";
import { connect } from "react-redux";
import { Link } from "react-router-dom";

import { CouponSheetProcessForm } from "../../../components/forms/CouponSheetProcessForm";
import queries from "../../../lib/queries";
import { routes } from "../../../lib/urls";

import type { Response } from "redux-query";
import { createStructuredSelector } from "reselect";

type State = {
  submitting: ?boolean,
  isProcessed: ?boolean,
  responseMsg: string,
  numCreated: number,
  numRemoved: number,
  errorMsg: string,
};

type DispatchProps = {|
  assignSheetCoupons: (payload: Object) => Promise<Response<any>>,
|};

type Props = {|
  ...DispatchProps,
|};

export class ProcessCouponAssignmentSheetPage extends React.Component<
  Props,
  State,
> {
  constructor(props: Props) {
    super(props);
    this.state = {
      submitting: false,
      isProcessed: false,
      responseMsg: "",
      numCreated: 0,
      numRemoved: 0,
      errorMsg: "",
    };
  }

  onSubmit = async (formData: Object, { setSubmitting }: Object) => {
    const result = await this.props.assignSheetCoupons(formData);
    await this.setState({
      submitting: false,
      isProcessed: true,
      responseMsg: result.body.message,
      numCreated: result.body.num_created,
      numRemoved: result.body.num_removed,
      errorMsg: result.body.error,
    });
    setSubmitting(false);
  };

  clearSuccess = async () => {
    await this.setState({
      submitting: false,
      isProcessed: false,
      responseMsg: "",
      numCreated: 0,
      numRemoved: 0,
      errorMsg: "",
    });
  };

  render() {
    const { isProcessed, responseMsg, numCreated, numRemoved, errorMsg } =
      this.state;
    return (
      <DocumentTitle
        title={`${SETTINGS.site_name} | ${PROCESS_COUPON_ASSIGNMENT_SHEET_PAGE_TITLE}`}
      >
        <div className="ecommerce-admin-body">
          <p>
            <Link to={routes.ecommerceAdmin.index}>
              Back to Ecommerce Admin
            </Link>
          </p>
          <h3>Process Coupon Assignment Sheets</h3>
          {isProcessed ? (
            <div className="coupon-result-div">
              {responseMsg ? (
                <div className="form-message form-success">
                  <p className="message-text">{responseMsg}</p>
                  <p className="message-text">
                    Number of Coupon Assignment created:{" "}
                    <strong>{numCreated}</strong>
                  </p>
                  <p className="message-text">
                    Number of Coupon Assignment removed:{" "}
                    <strong>{numRemoved}</strong>
                  </p>
                </div>
              ) : (
                <div className="form-message form-warning">
                  <p className="message-text">{errorMsg}</p>
                </div>
              )}

              <div>
                <input
                  type="button"
                  value="Process more sheets"
                  onClick={this.clearSuccess}
                />
              </div>
            </div>
          ) : (
            <CouponSheetProcessForm onSubmit={this.onSubmit} />
          )}
        </div>
      </DocumentTitle>
    );
  }
}

const assignSheetCoupons = (payload: Object) =>
  mutateAsync(queries.ecommerce.sheetCouponsAssignment(payload));

const mapStateToProps = createStructuredSelector({});

const mapDispatchToProps = {
  assignSheetCoupons: assignSheetCoupons,
};

export default compose(
  connect<Props, _, _, DispatchProps, _, _>(
    mapStateToProps,
    mapDispatchToProps,
  ),
)(ProcessCouponAssignmentSheetPage);
