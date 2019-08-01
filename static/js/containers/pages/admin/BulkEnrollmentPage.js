// @flow
/* global SETTINGS: false */
import React from "react"
import DocumentTitle from "react-document-title"
import { BULK_ENROLLMENT_PAGE_TITLE } from "../../../constants"
import { connect } from "react-redux"
import { connectRequest, mutateAsync } from "redux-query"
import { compose } from "redux"
import { createStructuredSelector } from "reselect"
import { Link } from "react-router-dom"

import { BulkEnrollmentForm } from "../../../components/forms/BulkEnrollmentForm"
import queries from "../../../lib/queries"
import { routes } from "../../../lib/urls"

import type { Response } from "redux-query"
import type {
  BulkCouponPayment,
  BulkCouponSendResponse,
  ProductMap
} from "../../../flow/ecommerceTypes"

type State = {
  selectedFile: ?Object,
  successData: ?Object,
  submitFailed: boolean
}

type StateProps = {|
  bulkCouponPayments: Array<BulkCouponPayment>,
  bulkCouponProducts: ProductMap
|}

type DispatchProps = {|
  submitBulkEnrollment: (
    usersFile: Object,
    productId: number,
    couponPaymentId: number
  ) => Promise<Response<BulkCouponSendResponse>>
|}

type Props = {|
  ...StateProps,
  ...DispatchProps
|}

export class BulkEnrollmentPage extends React.Component<Props, State> {
  submitRequest = async (
    payload: Object
  ): Promise<Response<BulkCouponSendResponse>> => {
    const { submitBulkEnrollment } = this.props

    return await submitBulkEnrollment(
      payload.users_file,
      payload.product_id,
      payload.coupon_payment_id
    )
  }

  render() {
    const { bulkCouponPayments, bulkCouponProducts } = this.props

    if (!bulkCouponPayments) {
      return (
        <DocumentTitle
          title={`${SETTINGS.site_name} | ${BULK_ENROLLMENT_PAGE_TITLE}`}
        >
          <div />
        </DocumentTitle>
      )
    }

    return (
      <DocumentTitle
        title={`${SETTINGS.site_name} | ${BULK_ENROLLMENT_PAGE_TITLE}`}
      >
        <div className="ecommerce-admin-body">
          <p>
            <Link to={routes.ecommerceAdmin.index}>
              Back to Ecommerce Admin
            </Link>
          </p>
          <h3>Bulk Enrollments</h3>
          {bulkCouponPayments.length === 0 ? (
            <div className="error">
              In order to perform bulk enrollment, there must be 100%-off
              coupons applied to products, and the coupons must be enabled. None
              were found.
            </div>
          ) : (
            <BulkEnrollmentForm
              bulkCouponPayments={bulkCouponPayments}
              productMap={bulkCouponProducts}
              submitRequest={this.submitRequest.bind(this)}
            />
          )}
        </div>
      </DocumentTitle>
    )
  }
}

const mapPropsToConfigs = () => [
  queries.ecommerceAdmin.bulkCouponPaymentsQuery()
]

const mapStateToProps = createStructuredSelector({
  bulkCouponPayments: queries.ecommerceAdmin.bulkCouponPaymentsSelector,
  bulkCouponProducts: queries.ecommerceAdmin.bulkCouponProductsSelector
})

const submitBulkEnrollment = (usersFile, productId, couponPaymentId) =>
  mutateAsync(
    queries.ecommerceAdmin.bulkEnrollmentMutation(
      usersFile,
      productId,
      couponPaymentId
    )
  )

const mapDispatchToProps = {
  submitBulkEnrollment
}

export default compose(
  connect(
    mapStateToProps,
    mapDispatchToProps
  ),
  connectRequest(mapPropsToConfigs)
)(BulkEnrollmentPage)
