// @flow
import React from "react"

import { formatPrice } from "../lib/ecommerce"

import type Decimal from "decimal.js-light"
type Props = {
  itemPrice: Decimal,
  totalPrice: Decimal,
  discount: ?string,
  numSeats: number,
  alreadyPaid: boolean
}
const B2BPurchaseSummary = ({
  itemPrice,
  totalPrice,
  numSeats,
  discount,
  alreadyPaid
}: Props) => (
  <div className="b2b-order-summary">
    <div className="container">
      <div className="row">
        <div className="col-12">
          <div className="total-paid">
            Total {alreadyPaid ? "Paid" : "Cost"}
          </div>
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
          <span className="quantity">{numSeats}</span>
        </div>
      </div>
      {discount ? (
        <div className="row discount-row">
          <div className="col-4">Discount:</div>
          <div className="col-8">
            <span className="discount">{formatPrice(discount)}</span>
          </div>
        </div>
      ) : null}
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
