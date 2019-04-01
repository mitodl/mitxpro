// @flow
import { assert } from "chai"
import _ from "lodash"

import { makeItem, makeCoupon } from "../factories/ecommerce"
import { calculatePrice, formatPrice } from "./ecommerce"

describe("ecommerce", () => {
  describe("calculatePrice", () => {
    it("calculates the price of an item", () => {
      const item = makeItem()
      assert.equal(calculatePrice(item), _.round(parseFloat(item.price), 2))
    })

    it("calculates a price of an item including the coupon", () => {
      const item = makeItem()
      const coupon = makeCoupon(item)
      assert.equal(
        calculatePrice(item, coupon),
        _.round(parseFloat(item.price) * (1 - coupon.amount), 2)
      )
    })

    it("rounds the output", () => {
      const item = {
        ...makeItem(),
        price: "123.456"
      }
      assert.equal(calculatePrice(item), 123.46)
    })
  })

  describe("formatPrice", () => {
    it("format price", () => {
      assert.equal(formatPrice(20), "$20")
      assert.equal(formatPrice(20.005), "$20.01")
      assert.equal(formatPrice(20.1), "$20.10")
      assert.equal(formatPrice(20.6059), "$20.61")
      assert.equal(formatPrice(20.6959), "$20.70")
      assert.equal(formatPrice(20.1234567), "$20.12")
    })

    it("returns an empty string if null or undefined", () => {
      assert.equal(formatPrice(null), "")
      assert.equal(formatPrice(undefined), "")
    })
  })
})
