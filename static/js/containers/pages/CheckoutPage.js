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
  formatPrice
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
          <div className="row">
            You are about to purchase the following program
          </div>
          {item.courses.map(course => (
            <div className="row course-row" key={course.id}>
              <img src={course.thumbnail_url} alt={course.title} />
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
                      {run.title}
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
        <React.Fragment>
          <div className="row">
            You are about to purchase the following course run
          </div>
          <div className="row course-row">
            <img src={item.thumbnail_url} alt={item.description} />
            <div className="title-column">
              <div className="title">{item.description}</div>
            </div>
          </div>
        </React.Fragment>
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
      <div className="checkout-page">
        {this.renderBasketItem(item)}
        <div className="row price-row">Price {formatPrice(item.price)}</div>
        {coupon ? (
          <div className="row discount-row">
            Discount applied {formatPrice(calculateDiscount(item, coupon))}
          </div>
        ) : null}
        <div className="row">Coupon (optional)</div>
        <div className="row coupon-code-row">
          <form onSubmit={this.submitCoupon}>
            <input
              type="text"
              value={
                (couponCode !== null ? couponCode : coupon && coupon.code) || ""
              }
              onChange={this.updateCouponCode}
            />
            <button type="submit">Update</button>
          </form>
        </div>
        <div className="row total-row">
          Total {formatPrice(calculatePrice(item, coupon))}
        </div>
        {errors ? <div className="error">Error: {errors}</div> : null}
        <button className="checkout" onClick={this.submit}>
          Place your order
        </button>
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
