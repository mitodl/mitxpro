// @flow
import { assert } from "chai"
import Decimal from "decimal.js-light"
import moment from "moment"
import * as R from "ramda"

import { makeItem, makeCouponSelection } from "../factories/ecommerce"
import {
  calcSelectedRunIds,
  calculatePrice,
  calculateTax,
  calculateTotalAfterTax,
  formatPrice,
  formatNumber,
  formatDiscount,
  formatRunTitle,
} from "./ecommerce"
import { makeCourseRun } from "../factories/course"
import { PRODUCT_TYPE_COURSERUN, PRODUCT_TYPE_PROGRAM } from "../constants"

describe("ecommerce", () => {
  describe("calculatePrice", () => {
    it("calculates the price of an item", () => {
      const item = {
        ...makeItem(),
        price: "123.45",
      }
      assert.equal(calculatePrice(item), item.price)
    })

    it("calculates a price of an item including the coupon", () => {
      const item = {
        ...makeItem(),
        price: "123.45",
      }
      const coupon = {
        ...makeCouponSelection(item),
        amount: "0.5",
      }
      assert.equal(
        calculatePrice(item, coupon).toString(),
        new Decimal("61.72").toString(),
      )
    })
  })

  describe("calculateTax", () => {
    ;[
      ["100", "0", 20, "20"],
      ["123", "1", 20, "0"],
      ["200", "0.5", 20, "20"],
    ].forEach(([price, discountAmount, taxRate, tax]) => {
      it("calculates the tax of an item price", () => {
        const item = {
          ...makeItem(),
          price: price,
        }
        const coupon = {
          ...makeCouponSelection(item),
          amount: discountAmount,
        }
        assert.equal(calculateTax(item, coupon, taxRate), tax)
      })
    })
  })

  describe("calculateTotalAfterTax", () => {
    ;[
      ["100", "0", 20, "120"],
      ["123", "1", 20, "0"],
      ["200", "0.5", 20, "120"],
    ].forEach(([price, discountAmount, taxRate, tax]) => {
      it("calculates the total including the tax for an item", () => {
        const item = {
          ...makeItem(),
          price: price,
        }
        const coupon = {
          ...makeCouponSelection(item),
          amount: discountAmount,
        }
        assert.equal(calculateTotalAfterTax(item, coupon, taxRate), tax)
      })
    })
  })

  describe("formatPrice", () => {
    it("format price", () => {
      assert.equal(formatPrice(20), "$20.00")
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

  describe("formatNumber", () => {
    it("format a number", () => {
      assert.equal(formatNumber(20), "20")
      assert.equal(formatNumber(20.005), "20.01")
      assert.equal(formatNumber(20.1), "20.10")
      assert.equal(formatNumber(20.6059), "20.61")
      assert.equal(formatNumber(20.6959), "20.70")
      assert.equal(formatNumber(20.1234567), "20.12")
      assert.equal(formatNumber(0), "0")
    })

    it("returns an empty string if null or undefined", () => {
      assert.equal(formatNumber(null), "")
      assert.equal(formatNumber(undefined), "")
    })
  })

  describe("formatDiscount", () => {
    it("format a discount", () => {
      assert.equal(formatDiscount(20), "-$20.00")
      assert.equal(formatDiscount(-20), "-$20.00")
      assert.equal(formatDiscount(20), "-$20.00")
      assert.equal(formatDiscount(20.0), "-$20.00")
      assert.equal(formatDiscount(20.0), "-$20.00")
      assert.equal(formatDiscount(-20.0), "-$20.00")
      assert.equal(formatDiscount(20.1), "-$20.10")
      assert.equal(formatDiscount(20.1), "-$20.10")
      assert.equal(formatDiscount(20.6959), "-$20.70")
      assert.equal(formatDiscount(-20.6959), "-$20.70")
      assert.equal(formatDiscount(20.6959), "-$20.70")
      assert.equal(formatDiscount(0.0), "$0.00")
      assert.equal(formatDiscount(0.0), "$0.00")
    })

    it("returns $0 string if null or undefined", () => {
      assert.equal(formatDiscount(null), "$0.00")
      assert.equal(formatDiscount(undefined), "$0.00")
    })
  })

  describe("formatRunTitle", () => {
    it("creates text based on the run's dates", () => {
      const run = makeCourseRun()
      assert.equal(
        formatRunTitle(run),
        `${moment(run.start_date).format("ll")} - ${moment(run.end_date).format(
          "ll",
        )}`,
      )
    })

    it("swaps out missing pieces with a question mark", () => {
      const run = {
        ...makeCourseRun(),
        start_date: null,
        end_date: null,
      }
      assert.equal(formatRunTitle(run), "? - ?")
    })
  })

  describe("calcSelectedRunIds", () => {
    let programBasketItem

    beforeEach(() => {
      programBasketItem = makeItem(PRODUCT_TYPE_PROGRAM)
      // Set incremental run_tag values for each course run in each course ("R1", "R2", "R3", etc.)
      programBasketItem.courses.map((course, courseIndex) => {
        assert.isAbove(course.courseruns.length, 1)
        course.courseruns.map((courseRun, courseRunIndex) => {
          programBasketItem.courses[courseIndex].courseruns[
            courseRunIndex
          ].run_tag = `R${courseRunIndex + 1}`
        })
      })
    })

    it("gets the correct course run selections for a program product with a run tag", () => {
      programBasketItem.run_tag = "R2"
      const expectedResult = R.compose(
        R.fromPairs,
        R.map((course) =>
          // Expecting index 1 since the run_tag is "R2", and those values were incrementally generated
          // starting with "R1"
          [course.id, course.courseruns[1].id],
        ),
      )(programBasketItem.courses)
      const result = calcSelectedRunIds(programBasketItem)
      assert.deepEqual(result, expectedResult)
    })

    it("gets the correct course run selections for a program product with preselect id", () => {
      const preselectRunId = programBasketItem.courses[0].courseruns[1].id
      const expectedResult = R.compose(
        R.fromPairs,
        R.map((course) => [course.id, course.courseruns[1].id]),
      )(programBasketItem.courses)
      const result = calcSelectedRunIds(programBasketItem, preselectRunId)
      assert.deepEqual(result, expectedResult)
    })

    it("returns no course run selections if there isn't a matching one for every course", () => {
      programBasketItem.run_tag = "R2"
      programBasketItem.courses[1].courseruns[1].run_tag = "notR2"
      const result = calcSelectedRunIds(programBasketItem)
      assert.deepEqual(result, {})
    })

    it("returns no course run selections if the course list is empty", () => {
      programBasketItem.courses = []
      const result = calcSelectedRunIds(programBasketItem)
      assert.deepEqual(result, {})
    })

    it("gets the correct course run selections if the product itself is a course run", () => {
      const courseRunBasketItem = makeItem(PRODUCT_TYPE_COURSERUN)
      const result = calcSelectedRunIds(courseRunBasketItem)
      assert.deepEqual(result, {
        [courseRunBasketItem.courses[0].id]: courseRunBasketItem.object_id,
      })
    })
  })
})
