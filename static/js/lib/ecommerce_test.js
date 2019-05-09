// @flow
import { assert } from "chai"
import Decimal from "decimal.js-light"
import moment from "moment"

import {
  makeItem,
  makeCouponSelection,
  makeBulkCouponPayment,
  makeProduct
} from "../factories/ecommerce"
import {
  calculatePrice,
  formatPrice,
  formatRunTitle,
  createProductMap
} from "./ecommerce"
import {
  PRODUCT_TYPE_COURSE,
  PRODUCT_TYPE_COURSERUN,
  PRODUCT_TYPE_PROGRAM
} from "../constants"
import { makeCourseRun } from "../factories/course"

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
        ...makeCouponSelection(item),
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

  describe("createProductMap", () => {
    it("creates a map of product type to a list of matching products", () => {
      const firstPayment = makeBulkCouponPayment(),
        secondPayment = makeBulkCouponPayment(),
        firstProduct = makeProduct(),
        secondProduct = makeProduct(),
        thirdProduct = makeProduct()

      firstProduct.product_type = PRODUCT_TYPE_COURSE
      secondProduct.product_type = PRODUCT_TYPE_COURSE
      thirdProduct.product_type = PRODUCT_TYPE_PROGRAM

      firstPayment.products = [firstProduct, secondProduct]
      secondPayment.products = [firstProduct, thirdProduct]
      const bulkCouponPayments = [firstPayment, secondPayment]

      assert.deepEqual(createProductMap(bulkCouponPayments), {
        [PRODUCT_TYPE_COURSE]:    [firstProduct, secondProduct],
        [PRODUCT_TYPE_PROGRAM]:   [thirdProduct],
        [PRODUCT_TYPE_COURSERUN]: []
      })
    })
  })

  describe("formatRunTitle", () => {
    it("creates text based on the run's dates", () => {
      const run = makeCourseRun()
      assert.equal(
        formatRunTitle(run),
        `${moment(run.start_date).format("ll")} - ${moment(run.end_date).format(
          "ll"
        )}`
      )
    })

    it("swaps out missing pieces with a question mark", () => {
      const run = {
        ...makeCourseRun(),
        start_date: null,
        end_date:   null
      }
      assert.equal(formatRunTitle(run), "? - ?")
    })
  })
})
