// @flow
import React from "react"
import { shallow } from "enzyme"
import { assert } from "chai"

import B2BPurchaseSummary from "./B2BPurchaseSummary"

import { formatPrice } from "../lib/ecommerce"

describe("B2BPurchaseSummary", () => {
  [true, false].forEach(alreadyPaid => {
    [true, false].forEach(hasDiscount => {
      it(`renders a summary of a B2B order ${
        alreadyPaid ? "after" : "before"
      } payment${hasDiscount ? ", with a discount" : ""}`, () => {
        const itemPrice = "123.45",
          totalPrice = hasDiscount ? "196.90" : "246.90",
          numSeats = 2,
          discount = hasDiscount ? "50" : null

        const wrapper = shallow(
          <B2BPurchaseSummary
            itemPrice={itemPrice}
            totalPrice={totalPrice}
            numSeats={numSeats}
            alreadyPaid={alreadyPaid}
            discount={discount}
          />
        )
        assert.equal(wrapper.find(".quantity").text(), String(numSeats))
        assert.equal(wrapper.find(".item-price").text(), formatPrice(itemPrice))
        assert.equal(
          wrapper.find(".total-price").text(),
          formatPrice(totalPrice)
        )
        if (hasDiscount) {
          assert.equal(wrapper.find(".discount").text(), formatPrice(discount))
        } else {
          assert.isFalse(wrapper.find(".discount").exists())
        }
        assert.equal(
          wrapper.find(".total-paid").text(),
          `Total ${alreadyPaid ? "Paid" : "Cost"}`
        )
      })
    })
  })
})
