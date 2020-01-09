// @flow
import React from "react"
import { ErrorMessage, Field, Formik, Form } from "formik"
import Decimal from "decimal.js-light"
import { curry } from "ramda"

import B2BPurchaseSummary from "../B2BPurchaseSummary"
import ProductSelector from "../input/ProductSelector"

import type {
  B2BCouponStatusPayload,
  B2BCouponStatusResponse,
  ProductDetail
} from "../../flow/ecommerceTypes"

type Props = {
  products: Array<ProductDetail>,
  onSubmit: Function,
  requestPending: boolean,
  couponStatus: ?B2BCouponStatusResponse,
  clearCouponStatus: () => void,
  fetchCouponStatus: (payload: B2BCouponStatusPayload) => Promise<*>,
  contractNumber: ?string
}

const errorMessageRenderer = msg => <span className="error">{msg}</span>

export const validate = (values: Object) => {
  const errors = {}

  const numSeats = parseInt(values.num_seats)
  if (isNaN(numSeats) || numSeats <= 0) {
    errors.num_seats = "Number of Seats is required"
  }

  if (!values.email.includes("@")) {
    errors.email = "Email is required"
  }

  if (!values.product) {
    errors.product = "No product selected"
  }

  return errors
}

class B2BPurchaseForm extends React.Component<Props> {
  applyCoupon = curry(
    async (values: Object, setFieldError: Function, event: Event) => {
      const { clearCouponStatus, fetchCouponStatus } = this.props

      event.preventDefault()

      if (!values.coupon) {
        clearCouponStatus()
        return
      }

      if (!values.product) {
        setFieldError("coupon", "No product selected")
        return
      }

      const response = await fetchCouponStatus({
        product_id: values.product,
        code:       values.coupon.trim()
      })
      if (response.status !== 200) {
        setFieldError("coupon", "Invalid coupon code")
      }
    }
  )

  renderForm = ({ values, setFieldError }: Object) => {
    const {
      products,
      requestPending,
      couponStatus,
      contractNumber
    } = this.props

    let itemPrice = new Decimal(0),
      totalPrice = new Decimal(0),
      discount
    const productId = parseInt(values.product)
    const product = products.find(product => product.id === productId)
    const productVersion = product ? product.latest_version : null
    let numSeats = parseInt(values.num_seats)

    if (productVersion && productVersion.price !== null) {
      itemPrice = new Decimal(productVersion.price)
      if (!isNaN(numSeats)) {
        totalPrice = itemPrice.times(numSeats)

        if (couponStatus) {
          discount = new Decimal(couponStatus.discount_percent)
            .times(itemPrice)
            .times(numSeats)
          totalPrice = totalPrice.minus(discount)
        }
      }
    }
    numSeats = isNaN(numSeats) ? 0 : numSeats

    return (
      <Form className="b2b-purchase-form container">
        <div className="row">
          <div className="col-lg-12">
            <div className="title">Bulk Seats</div>
          </div>
        </div>
        <div className="row">
          <div className="col-lg-5">
            <p className="purchase-title">
              Purchase one or more seats for your team.
            </p>
            <label htmlFor="product">
              <Field
                component={ProductSelector}
                products={products}
                name="product"
              />
              <ErrorMessage name="product" render={errorMessageRenderer} />
            </label>

            <label htmlFor="num_seats">
              <span className="description">*Number of Seats:</span>
              <Field type="text" name="num_seats" className="num-seats" />
              <ErrorMessage name="num_seats" render={errorMessageRenderer} />
            </label>

            <label htmlFor="email">
              <span className="description">*Email Address:</span>
              <Field type="text" name="email" />
              <span className="explanation">
                * We will email the link to the enrollment codes to this
                address.
              </span>
              <ErrorMessage name="email" render={errorMessageRenderer} />
            </label>

            {contractNumber && (
              <label htmlFor="contract_number">
                <span className="description">Contract Number:</span>
                <Field
                  type="text"
                  name="contract_number"
                  readOnly={true}
                  value={contractNumber}
                />
              </label>
            )}

            <label htmlFor="coupon">
              <span className="coupon-description">Discount code:</span>
              <div className="coupon-input-container">
                <Field type="text" name="coupon" />
                <button
                  className="apply-button"
                  onClick={this.applyCoupon(values, setFieldError)}
                >
                  Apply
                </button>
              </div>
              <ErrorMessage name="coupon" render={errorMessageRenderer} />
            </label>
          </div>
          <div className="col-lg-3" />
          <div className="col-lg-4">
            <B2BPurchaseSummary
              itemPrice={itemPrice}
              totalPrice={totalPrice}
              discount={discount}
              numSeats={numSeats}
              alreadyPaid={false}
            />

            <button
              className="checkout-button"
              type="submit"
              disabled={requestPending}
            >
              Place order
            </button>
          </div>
        </div>
      </Form>
    )
  }

  render() {
    const { onSubmit, contractNumber } = this.props
    return (
      <Formik
        onSubmit={onSubmit}
        initialValues={{
          num_seats:       "",
          email:           "",
          product:         "",
          coupon:          "",
          contract_number: contractNumber || ""
        }}
        validate={validate}
        render={this.renderForm}
      />
    )
  }
}

export default B2BPurchaseForm
