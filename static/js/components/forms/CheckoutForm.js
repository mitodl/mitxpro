// @flow
/* global SETTINGS: false */
import React from "react"
import { Formik, Field, Form } from "formik"
import { Modal, ModalHeader, ModalBody } from "reactstrap"

import Markdown from "../Markdown"

import { ZendeskAPI } from "react-zendesk"

import { formatErrors, formatSuccessMessage } from "../../lib/form"
import {
  calculateDiscount,
  calculatePrice,
  formatPrice,
  formatRunTitle
} from "../../lib/ecommerce"

import type {
  BasketItem,
  BasketResponse,
  CouponSelection
} from "../../flow/ecommerceTypes"
export type SetFieldError = (fieldName: string, fieldValue: any) => void
export type Values = {
  runs: { [number]: string },
  couponCode: ?string,
  dataConsent: boolean
}
export type Actions = {
  setFieldError: SetFieldError,
  setErrors: (errors: Object) => void,
  setSubmitting: (submitting: boolean) => void,
  setValues: (values: Values) => void,
  resetForm: () => void
}
type Errors = {
  runs?: string,
  coupons?: string,
  items?: string,
  data_consents?: string,
  genericBasket: boolean,
  genericSubmit: boolean
}
type CommonProps = {
  item: BasketItem,
  basket: BasketResponse,
  coupon: ?CouponSelection,
  requestPending: boolean,
  onSubmit: (Values, Actions) => Promise<void>,
  submitCoupon: (
    couponCode: ?string,
    setFieldError: SetFieldError
  ) => Promise<void>,
  updateProduct: (
    productId: number | string,
    runId: number,
    setFieldError: SetFieldError
  ) => Promise<void>
}
type OuterProps = CommonProps & {
  couponCode: ?string,
  selectedRuns: Object,
  basket: BasketResponse
}
type InnerProps = CommonProps &
  Actions & {
    errors: Errors,
    values: Values,
    onMount: () => void
  }

type InnerState = {
  dataSharingModalVisibility: boolean
}

export const renderGenericError = () => {
  return (
    <div className="error">
      Something went wrong. Please contact us at{" "}
      <u>
        <a
          href="https://xpro.zendesk.com/hc/en-us/requests/new"
          target="_blank"
          rel="noopener noreferrer"
        >
          Customer Support
        </a>
      </u>
      .
    </div>
  )
}

export class InnerCheckoutForm extends React.Component<InnerProps, InnerState> {
  // HACK: This helps to prevent a React unmounted warning if we redirect away from the page before we're done
  //       managing the state.
  isMounted = false

  constructor(props: InnerProps) {
    super(props)
    this.state = {
      dataSharingModalVisibility: false
    }
  }

  componentDidMount() {
    this.isMounted = true
    this.props.onMount()
  }

  componentWillUnmount() {
    this.isMounted = false
  }

  renderBasketItem = () => {
    const {
      item,
      values,
      setFieldError,
      setValues,
      resetForm,
      updateProduct
    } = this.props

    if (item.type === "program") {
      return (
        <React.Fragment>
          {item.courses.map(course => (
            <div className="flex-row item-row" key={course.id}>
              <div className="flex-row item-column">
                <img src={course.thumbnail_url} alt={course.title} />
              </div>
              <div className="title-column">
                <div className="title">{course.title}</div>
                <Field
                  component="select"
                  name={`runs.${course.id}`}
                  className="run-selector"
                >
                  <option value={""} key={"null"}>
                    Select a course run
                  </option>
                  {course.courseruns.map(run => (
                    <option value={run.id} key={run.id}>
                      {formatRunTitle(run)}
                    </option>
                  ))}
                </Field>
              </div>
            </div>
          ))}
        </React.Fragment>
      )
    } else {
      const course = item.courses[0]
      return (
        <div className="flex-row item-row">
          <div className="flex-row item-column">
            <img src={item.thumbnail_url} alt={item.content_title} />
          </div>
          <div className="title-column">
            <div className="title">{item.content_title}</div>
            <Field
              component="select"
              name={`runs.${course.id}`}
              className="run-selector"
              onChange={async e => {
                setValues({
                  ...values,
                  runs: {
                    ...values.runs,
                    [course.id]: e.target.value
                  }
                })

                if (!e.target.value) {
                  return
                }

                const selectedRunId = parseInt(e.target.value)
                const run = course.courseruns.find(
                  run => run.id === selectedRunId
                )
                if (run && run.product_id) {
                  await updateProduct(run.product_id, run.id, setFieldError)
                  if (this.isMounted) {
                    resetForm()
                  }
                }
              }}
            >
              <option value={""} key={"null"}>
                Select a course run
              </option>
              {course.courseruns.map(run =>
                run.product_id ? (
                  <option value={run.id} key={run.id}>
                    {formatRunTitle(run)}
                  </option>
                ) : null
              )}
            </Field>
          </div>
        </div>
      )
    }
  }

  toggleDataSharingModalVisibility = () => {
    const { dataSharingModalVisibility } = this.state
    this.setState({
      dataSharingModalVisibility: !dataSharingModalVisibility
    })
  }

  isPromoCodeApplied = () => {
    const { coupon, errors, values } = this.props

    return (
      !errors.coupons &&
      !errors.genericBasket &&
      values.couponCode &&
      values.couponCode !== "" &&
      coupon &&
      coupon.code === values.couponCode.trim()
    )
  }

  render() {
    const {
      basket,
      errors,
      requestPending,
      values,
      setFieldError,
      item,
      coupon,
      submitCoupon
    } = this.props
    const { dataSharingModalVisibility } = this.state

    if (!basket) {
      return null
    }

    const dataConsent = basket.data_consents[0]
    if (SETTINGS.zendesk_config.help_widget_enabled) {
      ZendeskAPI("webWidget", "helpCenter:setSuggestions", {
        search: item.content_title
      })
    }

    return (
      <React.Fragment>
        <Form className="checkout-page container">
          <div className="row header">
            <div className="col-12">
              <div className="page-title">Checkout</div>
              <div className="purchase-text">
                You are about to purchase the following:
              </div>
              <div className="item-type">
                {item.type === "program" ? "Program" : "Course"}
              </div>
              <hr />
              {item.type === "program" ? (
                <span className="description">{item.content_title}</span>
              ) : null}
            </div>
          </div>
          <div className="row">
            <div className="col-lg-7">
              {this.renderBasketItem()}
              {formatErrors(errors.runs)}
              <div className="enrollment-input">
                <div className="enrollment-row">
                  Enrollment / Promotional Code
                </div>
                <div className="flex-row coupon-code-row">
                  <Field
                    type="text"
                    name="couponCode"
                    className="coupon-code-entry"
                    onKeyDown={event => {
                      if (event.key === "Enter") {
                        event.preventDefault()
                        submitCoupon(values.couponCode, setFieldError)
                      }
                    }}
                  />
                  <button
                    className="apply-button"
                    type="button"
                    disabled={requestPending}
                    onClick={() =>
                      submitCoupon(values.couponCode, setFieldError)
                    }
                  >
                    Apply
                  </button>
                </div>
                {this.isPromoCodeApplied() &&
                  formatSuccessMessage("Success! Promo Code applied.")}
                {errors.genericBasket
                  ? renderGenericError()
                  : formatErrors(errors.coupons)}
              </div>
              {dataConsent ? (
                <div className="data-consent">
                  <div className="data-consent-row">
                    <Field
                      type="checkbox"
                      name="dataConsent"
                      value={true}
                      checked={values.dataConsent}
                    />
                    <span>
                      *By checking this box, I give my consent to MIT to
                      disclose data to {dataConsent.company.name}. View the{" "}
                      <a
                        onClick={() => this.toggleDataSharingModalVisibility()}
                      >
                        Data Sharing Policy
                      </a>
                      .
                    </span>
                  </div>
                  {formatErrors(errors.data_consents)}
                </div>
              ) : null}
            </div>
            <div className="col-lg-5 order-summary-container">
              <div className="order-summary">
                <div className="title">Order Summary</div>
                <div className="flex-row price-row">
                  <span>Price:</span>
                  <span>{formatPrice(item.price)}</span>
                </div>
                {coupon ? (
                  <div className="flex-row discount-row">
                    <span>Discount:</span>
                    <span>{formatPrice(calculateDiscount(item, coupon))}</span>
                  </div>
                ) : null}
                <div className="bar" />
                <div className="flex-row total-row">
                  <span>Total:</span>
                  <span>{formatPrice(calculatePrice(item, coupon))}</span>
                </div>
              </div>
              <div>
                <button
                  className="checkout-button"
                  type="submit"
                  disabled={requestPending}
                >
                  Place your order
                </button>
                {errors.genericSubmit
                  ? renderGenericError()
                  : formatErrors(errors.items)}
                <div className="submit-links">
                  By placing my order I agree to the{" "}
                  <a href="/terms-of-service/" target="_blank">
                    Terms of Service
                  </a>
                  ,{" "}
                  <a href="/honor-code/" target="_blank">
                    Refund Policy
                  </a>
                  , and{" "}
                  <a href="/privacy-policy/" target="_blank">
                    Privacy Policy
                  </a>
                  .
                </div>
              </div>
            </div>
          </div>
        </Form>
        {dataConsent ? (
          <Modal
            isOpen={dataSharingModalVisibility}
            toggle={this.toggleDataSharingModalVisibility}
            className="data-consent-modal"
          >
            <ModalHeader toggle={this.toggleDataSharingModalVisibility}>
              Data Sharing Policy
            </ModalHeader>
            <ModalBody>
              <Markdown source={dataConsent.consent_text} />
            </ModalBody>
          </Modal>
        ) : null}
      </React.Fragment>
    )
  }
}

export class CheckoutForm extends React.Component<OuterProps> {
  validate = (values: Values) => {
    const { basket, item } = this.props
    const errors = {}
    const selectedRuns = values.runs

    const missingCourses = []
    for (const course of item.courses) {
      if (!selectedRuns[course.id]) {
        missingCourses.push(course.title)
      }
    }

    if (missingCourses.length) {
      errors.runs = `No run selected for ${missingCourses.join(", ")}`
    }

    if (basket && basket.data_consents[0] && !values.dataConsent) {
      errors.data_consents =
        "User must consent to the Data Sharing Policy to use the coupon."
    }

    return errors
  }

  render() {
    const {
      basket,
      onSubmit,
      coupon,
      couponCode,
      item,
      requestPending,
      selectedRuns,
      submitCoupon,
      updateProduct
    } = this.props

    return (
      <Formik
        onSubmit={onSubmit}
        initialValues={{
          couponCode:  couponCode || (coupon ? coupon.code : ""),
          runs:        selectedRuns,
          dataConsent: false
        }}
        validate={this.validate}
        render={props => (
          <InnerCheckoutForm
            {...props}
            basket={basket}
            item={item}
            coupon={coupon}
            requestPending={requestPending}
            onSubmit={onSubmit}
            submitCoupon={submitCoupon}
            updateProduct={updateProduct}
            onMount={() => {
              // only submit if there is a couponCode query parameter,
              // and if it's different than one in the existing coupon
              if (couponCode && (!coupon || coupon.code !== couponCode)) {
                submitCoupon(couponCode, props.setFieldError)
              }
            }}
          />
        )}
      />
    )
  }
}
