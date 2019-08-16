// @flow
import React from "react"

import { formatPrice } from "../lib/ecommerce"

import type Decimal from "decimal.js-light"
type Props = {
  itemPrice: Decimal,
  totalPrice: Decimal,
  numSeats: ?number
}
const B2BPurchaseSummary = ({ itemPrice, totalPrice, numSeats }: Props) => (
  <div className="b2b-order-summary">
    <div className="container">
      <div className="row">
        <div className="col-12">
          <div className="total-paid">Total Paid</div>
        </div>
      </div>
      <div className="row">
        <div className="col-4">Price:</div>
        <div className="col-8">
          <span className="item-price">{formatPrice(itemPrice)}</span>
        </div>
      </div>
      <div className="row">
        <div className="col-4">Quantity:</div>
        <div className="col-8">
          <span className="quantity">{numSeats || ""}</span>
        </div>
      </div>
    </div>
    <div className="bar" />
    <div className="container">
      <div className="row">
        <div className="col-4">Total:</div>
        <div className="col-8">
          <span className="total-price">{formatPrice(totalPrice)}</span>
        </div>
      </div>
    </div>
  </div>
)
export default B2BPurchaseSummary
