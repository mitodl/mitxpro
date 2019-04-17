// @flow
import casual from "casual-browserify"
import R from "ramda"

import { makeCourseRun } from "./course"
import { incrementer } from "./util"

import type { BasketItem, BasketResponse, Coupon } from "../flow/ecommerceTypes"

const genBasketItemId = incrementer()

export const makeItem = (): BasketItem => ({
  type:          casual.random_element(["courserun", "course", "program"]),
  course_runs:   R.range(0, 4).map(() => makeCourseRun()),
  // $FlowFixMe: flow doesn't understand generators well
  id:            genBasketItemId.next().value,
  description:   casual.text,
  price:         String(casual.double(0, 100)),
  thumbnail_url: casual.url
})

export const makeCoupon = (item: ?BasketItem): Coupon => ({
  code:    casual.word,
  amount:  String(casual.double(0, 1)),
  targets: item ? [item.id] : []
})

export const makeBasketResponse = (): BasketResponse => ({
  items:   [makeItem()],
  coupons: [makeCoupon()]
})
