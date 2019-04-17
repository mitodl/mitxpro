// @flow
import React from "react"
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
  CheckoutResponse
} from "../../flow/ecommerceTypes"

type Props = {
  basket: ?BasketResponse,
  checkout: () => Promise<Response<CheckoutResponse>>,
  updateBasket: (payload: BasketPayload) => Promise<*>
}
type State = {
  couponCode: string | null,
  errors: string | Array<string> | null
}
export class CheckoutPage extends React.Component<Props, State> {
  state = {
    couponCode: null,
    errors:     null
  }

  submit = async () => {
    const { checkout } = this.props

    const response = await checkout()
    const { url, payload } = response.body
    const form = createCyberSourceForm(url, payload)
    const body: HTMLElement = (document.querySelector("body"): any)
    body.appendChild(form)
    form.submit()
  }

  updateCouponCode = (event: any) => {
    this.setState({
      couponCode: event.target.value
    })
  }

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
        <div className="row">
          You are about to purchase the following course
        </div>
        <div className="row course-row">
          <img src={item.thumbnail_url} alt={item.description} />
          <div className="description">{item.description}</div>
        </div>
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
