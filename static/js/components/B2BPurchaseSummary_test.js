// @flow
import React from "react"
import { shallow } from "enzyme"
import { assert } from "chai"

import B2BPurchaseSummary from "./B2BPurchaseSummary"

import { formatPrice } from "../lib/ecommerce"

describe("B2BPurchaseSummary", () => {
  it("renders a summary of a B2B order", () => {
    const itemPrice = "123.45",
      totalPrice = "246.90",
      numSeats = 2

    const wrapper = shallow(
      <B2BPurchaseSummary
        itemPrice={itemPrice}
        totalPrice={totalPrice}
        numSeats={numSeats}
      />
    )
    assert.equal(wrapper.find(".quantity").text(), String(numSeats))
    assert.equal(wrapper.find(".item-price").text(), formatPrice(itemPrice))
    assert.equal(wrapper.find(".total-price").text(), formatPrice(totalPrice))
  })
})
