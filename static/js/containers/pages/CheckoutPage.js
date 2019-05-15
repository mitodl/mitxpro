// @flow
import React from "react"
import * as R from "ramda"
import { connect } from "react-redux"
import { connectRequest, mutateAsync } from "redux-query"
import { compose } from "redux"

import queries from "../../lib/queries"
import {
  calculateDiscount,
  calculatePrice,
  formatPrice,
  formatRunTitle
} from "../../lib/ecommerce"
import { createCyberSourceForm } from "../../lib/form"

import type { Response } from "redux-query"
import type {
  BasketResponse,
  BasketPayload,
  CheckoutResponse,
  BasketItem
} from "../../flow/ecommerceTypes"

export const calcSelectedRunIds = (item: BasketItem): { [number]: number } => {
  if (item.type === "courserun") {
    const course = item.courses[0]
    return {
      [course.id]: item.object_id
    }
  }

  const courseLookup = {}
  for (const course of item.courses) {
    for (const run of course.courseruns) {
      courseLookup[run.id] = course.id
    }
  }

  const selectedRunIds = {}
  for (const runId of item.run_ids) {
    const courseId = courseLookup[runId]

    // there should only be one run selected for a course
    selectedRunIds[courseId] = runId
  }
  return selectedRunIds
}

type Props = {
  basket: ?BasketResponse,
  checkout: () => Promise<Response<CheckoutResponse>>,
  updateBasket: (payload: BasketPayload) => Promise<*>
}
type State = {
  couponCode: string | null,
  errors: string | Array<string> | null,
  selectedRuns: { [number]: { [number]: number } } | null
}
export class CheckoutPage extends React.Component<Props, State> {
  state = {
    couponCode:   null,
    selectedRuns: null,
    errors:       null
  }

  handleErrors = async (responsePromise: Promise<*>) => {
    const response = await responsePromise
    if (response.body.errors) {
      this.setState({ errors: response.body.errors })
      throw new Error("Received error from request")
    }
    return response
  }

  getSelectedRunIds = (item: BasketItem): { [number]: number } => {
    return {
      ...calcSelectedRunIds(item),
      ...this.state.selectedRuns
    }
  }

  submit = async () => {
    const { basket } = this.props

    if (!basket) {
      // if there is no basket there shouldn't be any submit button rendered
      throw new Error("Expected basket to exist")
    }

    // update basket with selected runs
    await this.updateBasket({
      items: basket.items.map(item => ({
        id:      item.id,
        // $FlowFixMe: flow doesn't understand that Object.values will return an array of number here
        run_ids: Object.values(this.getSelectedRunIds(item))
      }))
    })

    const {
      body: { url, payload, method }
    } = await this.checkout()

    if (method === "GET") {
      window.location = url
    } else {
      const form = createCyberSourceForm(url, payload)
      const body: HTMLElement = (document.querySelector("body"): any)
      body.appendChild(form)
      form.submit()
    }
  }

  updateCouponCode = (event: any) => {
    this.setState({
      couponCode: event.target.value
    })
  }

  updateSelectedRun = R.curry((courseId: number, event: any) => {
    const { selectedRuns } = this.state
    const runId = parseInt(event.target.value)
    this.setState({
      selectedRuns: {
        ...selectedRuns,
        [courseId]: runId
      }
    })
  })

  submitCoupon = async (e: Event) => {
    const { updateBasket } = this.props
    const { couponCode } = this.state

    e.preventDefault()

    const response = await updateBasket({
      coupons: couponCode
        ? [
          {
            code: couponCode
          }
        ]
        : []
    })
    const errors = response.status !== 200 ? response.body.errors : null
    this.setState({ errors })
  }

  // $FlowFixMe
  updateBasket = (...args) =>
    this.handleErrors(this.props.updateBasket(...args))
  // $FlowFixMe
  checkout = (...args) => this.handleErrors(this.props.checkout(...args))

  renderBasketItem = (item: BasketItem) => {
    const selectedRunIds = this.getSelectedRunIds(item)
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
                <select
                  className="run-selector"
                  onChange={this.updateSelectedRun(course.id)}
                  value={selectedRunIds[course.id] || ""}
                >
                  <option value={null} key={"null"}>
                    Select a course run
                  </option>
                  {course.courseruns.map(run => (
                    <option value={run.id} key={run.id}>
                      {formatRunTitle(run)}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          ))}
        </React.Fragment>
      )
    } else {
      return (
        <div className="flex-row item-row">
          <div className="flex-row item-column">
            <img src={item.thumbnail_url} alt={item.description} />
          </div>
          <div className="title-column">
            <div className="title">{item.description}</div>
          </div>
        </div>
      )
    }
  }

  render() {
    const { basket } = this.props
    const { couponCode, errors } = this.state

    if (!basket) {
      return null
    }

    const item = basket.items[0]
    if (!item) {
      return <div>No item in basket</div>
    }

    const coupon = basket.coupons.find(coupon =>
      coupon.targets.includes(item.id)
    )

    return (
      <div className="checkout-page container">
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
            {this.renderBasketItem(item)}
            <div className="enrollment-input">
              <div className="enrollment-row">
                Enrollment / Promotional Code
              </div>
              <form onSubmit={this.submitCoupon}>
                <div className="flex-row coupon-code-row">
                  <input
                    type="text"
                    className={errors ? "error-border" : ""}
                    value={
                      (couponCode !== null
                        ? couponCode
                        : coupon && coupon.code) || ""
                    }
                    onChange={this.updateCouponCode}
                  />
                  <button
                    className="apply-button"
                    type="button"
                    onClick={this.submitCoupon}
                  >
                    Apply
                  </button>
                </div>
                {errors ? <div className="error">Error: {errors}</div> : null}
              </form>
            </div>
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
            <button className="checkout-button" onClick={this.submit}>
              Place your order
            </button>
          </div>
        </div>
      </div>
    )
  }
}

const mapStateToProps = state => ({
  basket: state.entities.basket
})
const mapDispatchToProps = dispatch => ({
  checkout:     () => dispatch(mutateAsync(queries.ecommerce.checkoutMutation())),
  updateBasket: payload =>
    dispatch(mutateAsync(queries.ecommerce.basketMutation(payload)))
})
const mapPropsToConfigs = () => [queries.ecommerce.basketQuery()]

export default compose(
  connect(
    mapStateToProps,
    mapDispatchToProps
  ),
  connectRequest(mapPropsToConfigs)
)(CheckoutPage)
