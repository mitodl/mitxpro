// @flow
import React from "react"
import { connect } from "react-redux"
import { connectRequest, mutateAsync } from "redux-query"
import { compose } from "redux"

import queries from "../../lib/queries"
import { calculatePrice, formatPrice } from "../../lib/ecommerce"
import { createForm } from "../../lib/form"

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
  couponCode: string | null
}
export class CheckoutPage extends React.Component<Props, State> {
  state = {
    couponCode: null
  }

  submit = async () => {
    const { checkout } = this.props

    const response = await checkout()
    const { url, payload } = response.body
    const form = createForm(url, payload)
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

    await updateBasket({
      coupons: couponCode
        ? [
          {
            code: couponCode
          }
        ]
        : []
    })
  }

  render() {
    const { basket } = this.props
    const { couponCode } = this.state

    if (!basket) {
      return null
    }

    const item = basket.items[0]
    const coupon = item
      ? basket.coupons.find(coupon => coupon.targets.includes(item.id))
      : null

    if (!item) {
      return <div>No item in basket</div>
    }

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
            Discount applied {formatPrice(item.price * coupon.amount)}
          </div>
        ) : null}
        <div className="row">Coupon (optional)</div>
        <div className="row coupon-code-row">
          <form onSubmit={this.submitCoupon}>
            <input
              type="text"
              value={couponCode !== null ? couponCode : coupon && coupon.code}
              onChange={this.updateCouponCode}
            />
            <button type="submit">Update</button>
          </form>
        </div>
        <div className="row total-row">
          Total {formatPrice(calculatePrice(item, coupon))}
        </div>
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
