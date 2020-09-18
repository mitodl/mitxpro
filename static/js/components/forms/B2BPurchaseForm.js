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
  Product
} from "../../flow/ecommerceTypes"
import { findProductById } from "../../lib/ecommerce"

type Props = {
  products: Array<Product>,
  onSubmit: Function,
  requestPending: boolean,
  couponStatus: ?B2BCouponStatusResponse,
  clearCouponStatus: () => void,
  fetchCouponStatus: (payload: B2BCouponStatusPayload) => Promise<*>,
  contractNumber: ?string,
  discountCode: ?string,
  productId: ?string,
  seats: ?string
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

  if (!values.product.productId) {
    errors.product = "No product selected"
  }

  return errors
}

class B2BPurchaseForm extends React.Component<Props> {
  formikRef = React.createRef<Formik>()

  componentDidMount() {
    // on page load apply the coupon code provided in the URL query paramater
    const formikRef = this.formikRef
    if (formikRef) {
      const formikRefObj = formikRef.current
      if (formikRefObj && formikRefObj.state.values.coupon) {
        this.applyCoupon(
          formikRefObj.state.values,
          formikRefObj.setFieldError,
          formikRefObj.setFieldTouched,
          null
        )
      }
    }
  }

  applyCoupon = curry(
    async (
      values: Object,
      setFieldError: Function,
      setFieldTouched: Function,
      event: Event
    ) => {
      const { products, clearCouponStatus, fetchCouponStatus } = this.props

      if (event) {
        event.preventDefault()
      }

      if (!values.coupon) {
        clearCouponStatus()
        return
      }

      if (!values.product.productId) {
        setFieldError("coupon", "No product selected")
        setFieldTouched("coupon", true, false)
        return
      }

      const response = await fetchCouponStatus({
        product_id: values.product.productId,
        code:       values.coupon.trim()
      })
      if (response && response.status !== 200) {
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
      contractNumber,
      clearCouponStatus
    } = this.props

    let itemPrice = new Decimal(0),
      totalPrice = new Decimal(0),
      discount

    const product = findProductById(products, values.product.productId)
    const productVersion = product ? product.latest_version : null
    let numSeats = parseInt(values.num_seats)

    if (productVersion && productVersion.price !== null) {
      itemPrice = new Decimal(productVersion.price)
      if (!isNaN(numSeats)) {
        totalPrice = itemPrice.times(numSeats)
        // $FlowFixMe: product.id is not undefined
        if (couponStatus && couponStatus.product_id === product.id) {
          discount = new Decimal(couponStatus.discount_percent)
            .times(itemPrice)
            .times(numSeats)
          totalPrice = totalPrice.minus(discount)
        } else if (
          couponStatus &&
          product &&
          couponStatus.product_id !== product.id
        ) {
          values.coupon = this.props.discountCode || ""
          clearCouponStatus()
        }
      }
    }
    numSeats = isNaN(numSeats) ? 0 : numSeats

    return (
      <Form className="b2b-purchase-form container">
        <div className="row">
          <div className="col-lg-12">
            <div className="title">Order Form</div>
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
                values={values}
                applyCoupon={this.applyCoupon}
                setFieldError={setFieldError}
                setFieldTouched={setFieldTouched}
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
              By placing my order, I accept the{" "}
              <a href="/enterprise-terms-and-conditions/">
                MIT xPRO Enterprise Terms and Conditions.
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
          num_seats: this.props.seats || 1,
          email:     "",
          product:   {
            productId:    this.props.productId || "",
            programRunId: null
          },
          coupon:          this.props.discountCode || "",
          contract_number: this.props.contractNumber || ""
        }}
        validate={validate}
        render={this.renderForm}
        ref={this.formikRef}
      />
    )
  }
}

export default B2BPurchaseForm
