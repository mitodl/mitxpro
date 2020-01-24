// @flow
import React from "react"
import { ErrorMessage, Field, Formik, Form } from "formik"
import Decimal from "decimal.js-light"
import { curry } from "ramda"

import B2BPurchaseSummary from "../B2BPurchaseSummary"
import ProductSelector from "../input/ProductSelector"
import B2BCheckoutExplanation from "../B2BCheckoutExplanation"

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
  contractNumber: ?string,
  discountCode: ?string,
  productId: ?string
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
    async (
      values: Object,
      setFieldError: Function,
      setFieldTouched: Function,
      event: Event
    ) => {
      const { products, clearCouponStatus, fetchCouponStatus } = this.props

      event.preventDefault()

      if (!values.coupon) {
        clearCouponStatus()
        return
      }

      if (!values.product) {
        setFieldError("coupon", "No product selected")
        return
      }
      let productId = values.product
      if (isNaN(values.product)) {
        const _product = products.find(
          product => product.latest_version.readable_id === values.product
        )
        if (_product) {
          productId = _product.id
        }
      }

      const response = await fetchCouponStatus({
        product_id: productId,
        code:       values.coupon.trim()
      })
      if (response.status !== 200) {
        setFieldError("coupon", "Invalid coupon code")
        setFieldTouched("coupon", true, false)
      }
    }
  )

  renderForm = ({ values, setFieldError, setFieldTouched }: Object) => {
    const {
      products,
      requestPending,
      couponStatus,
      contractNumber
    } = this.props

    let itemPrice = new Decimal(0),
      totalPrice = new Decimal(0),
      discount,
      productId,
      product

    // product_id can be either a product readable_id or an integer value in query parameter.
    // in case of readable_id, we need to look inside the latest_version of product.
    if (isNaN(values.product)) {
      product = products.find(
        product => product.latest_version.readable_id === values.product
      )
      if (product !== undefined) {
        productId = product.id
      }
    } else {
      productId = parseInt(values.product)
      product = products.find(product => product.id === productId)
    }

    const productVersion = product ? product.latest_version : null
    const productType = product ? product.product_type : null
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
            <div className="title">Bulk Purchase Order</div>
          </div>
          <B2BCheckoutExplanation />
        </div>
        <div className="row">
          <div className="col-lg-5">
            <label htmlFor="product" className="mt-0">
              <Field
                component={ProductSelector}
                products={products}
                selectedProduct={product}
                productType={productType}
                name="product"
              />
              <ErrorMessage name="product" render={errorMessageRenderer} />
            </label>

            <label htmlFor="num_seats">
              <span className="description">
                *Number of enrollment codes to purchase:
              </span>
              <Field type="text" name="num_seats" className="num-seats" />
              <ErrorMessage name="num_seats" render={errorMessageRenderer} />
            </label>

            <label htmlFor="email">
              <span className="description">*Your email address:</span>
              <Field type="text" name="email" />
              <span className="explanation">
                * We will email the enrollment codes to this address.
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
                  onClick={this.applyCoupon(
                    values,
                    setFieldError,
                    setFieldTouched
                  )}
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
            <div className="description enterprise-terms-condition">
              By placing my order I accept the{" "}
              <a href="/enterprise-terms-and-conditions/">
                MIT xPRO Enterprise Sales Terms and Conditions
              </a>
            </div>
          </div>
        </div>
      </Form>
    )
  }

  render() {
    const { onSubmit } = this.props
    return (
      <Formik
        onSubmit={onSubmit}
        initialValues={{
          num_seats:      "",
          email:          "",
          product:        this.props.productId || "",
          coupon:         this.props.discountCode || "",
          contractNumber: this.props.contractNumber || ""
        }}
        validate={validate}
        render={this.renderForm}
      />
    )
  }
}

export default B2BPurchaseForm
