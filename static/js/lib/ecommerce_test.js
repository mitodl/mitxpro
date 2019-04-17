// @flow
import { assert } from "chai"
import Decimal from "decimal.js-light"

import { makeItem, makeCoupon } from "../factories/ecommerce"
import { calculatePrice, formatPrice } from "./ecommerce"

describe("ecommerce", () => {
  describe("calculatePrice", () => {
    it("calculates the price of an item", () => {
      const item = {
        ...makeItem(),
        price: "123.45"
      }
      assert.equal(calculatePrice(item), item.price)
    })

    it("calculates a price of an item including the coupon", () => {
      const item = {
        ...makeItem(),
        price: "123.45"
      }
      const coupon = {
        ...makeCoupon(item),
        amount: "0.5"
      }
      assert.equal(
        calculatePrice(item, coupon).toString(),
        new Decimal("61.72").toString()
      )
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
