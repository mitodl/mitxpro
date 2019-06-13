// @flow
import React from "react"
import { Formik, Field, Form } from "formik"
import { Modal, ModalHeader, ModalBody } from "reactstrap"

import Markdown from "../Markdown"

import { formatErrors } from "../../lib/form"
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
export type UpdateProduct = (
  productId: number,
  runId: number,
  setFieldError: SetFieldError
) => Promise<void>
export type Values = {
  runs: { [number]: string },
  couponCode: ?string,
  dataConsent: boolean
}
export type Actions = {
  setFieldError: SetFieldError,
  setErrors: (errors: Object) => void,
  setSubmitting: (submitting: boolean) => void,
  setValues: (values: Values) => void
}
type Errors = {
  runs?: string,
  coupons?: string,
  items?: string,
  dataConsent?: string
}
type CommonProps = {
  item: BasketItem,
  basket: BasketResponse,
  coupon: ?CouponSelection,
  onSubmit: (Values, Actions) => Promise<void>,
  submitCoupon: (
    couponCode: ?string,
    setFieldError: SetFieldError
  ) => Promise<void>,
  updateProduct: UpdateProduct
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

export class InnerCheckoutForm extends React.Component<InnerProps, InnerState> {
  constructor(props: InnerProps) {
    super(props)
    this.state = {
      dataSharingModalVisibility: false
    }
  }

  componentDidMount() {
    this.props.onMount()
  }

  renderBasketItem = () => {
    const { item, values, setFieldError, setValues, updateProduct } = this.props

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
            <img src={item.thumbnail_url} alt={item.description} />
          </div>
          <div className="title-column">
            <div className="title">{item.description}</div>
            <Field
              component="select"
              name={`runs.${course.id}`}
              className="run-selector"
              onChange={e => {
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
                  updateProduct(run.product_id, run.id, setFieldError)
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

  render() {
    const {
      basket,
      errors,
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
                <span className="description">{item.description}</span>
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
                    onClick={() =>
                      submitCoupon(values.couponCode, setFieldError)
                    }
                  >
                    Apply
                  </button>
                </div>
                {formatErrors(errors.coupons)}
              </div>
              {dataConsent ? (
                <div>
                  <div className="data-consent-row">
                    <Field type="checkbox" name="dataConsent" value={true} />
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
                  {formatErrors(errors.dataConsent)}
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
            </div>
          </div>
          <div className="row">
            <div className="col-lg-7" />
            <div className="col-lg-5">
              <button className="checkout-button" type="submit">
                Place your order
              </button>
              {formatErrors(errors.items)}
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

    if (basket) {
      const dataConsent = basket.data_consents[0]
      if (dataConsent && !dataConsent.consent_date) {
        if (!values.dataConsent) {
          errors.dataConsent =
            "User must consent to the Data Sharing Policy to use the coupon."
        }
      }
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
      selectedRuns,
      submitCoupon,
      updateProduct
    } = this.props

    return (
      <Formik
        onSubmit={onSubmit}
        initialValues={{
          couponCode: couponCode || (coupon ? coupon.code : ""),
          runs:       selectedRuns
        }}
        validate={this.validate}
        render={props => (
          <InnerCheckoutForm
            {...props}
            basket={basket}
            item={item}
            coupon={coupon}
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
