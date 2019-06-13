// @flow
import casual from "casual-browserify"
import { range } from "ramda"

import { makeCourse } from "./course"
import { incrementer } from "./util"

import type {
  BasketItem,
  BasketResponse,
  BulkCouponPayment,
  CouponSelection,
  CouponPayment,
  CouponPaymentVersion,
  Company,
  DataConsentUser,
  Product
} from "../flow/ecommerceTypes"
import { PRODUCT_TYPE_COURSERUN, PRODUCT_TYPE_PROGRAM } from "../constants"

const genBasketItemId = incrementer()
const genNextObjectId = incrementer()
const genProductId = incrementer()

const genDataConsentUserId = incrementer()

export const makeDataConsent = (): DataConsentUser => ({
  // $FlowFixMe: flow doesn't understand generators well
  id:           genDataConsentUserId.next().value,
  company:      makeCompany(),
  consent_date: casual.moment.format(),
  consent_text: casual.text
})

export const makeItem = (itemType: ?string): BasketItem => {
  const basketItemType =
    itemType ||
    casual.random_element([PRODUCT_TYPE_COURSERUN, PRODUCT_TYPE_PROGRAM])
  const numCourses = basketItemType === PRODUCT_TYPE_COURSERUN ? 1 : 4
  const courses = range(0, numCourses).map(() => makeCourse())
  const runIds = courses.map(course => course.courseruns[0].id)

  return {
    type:          basketItemType,
    courses:       courses,
    // $FlowFixMe: flow doesn't understand generators well
    id:            genBasketItemId.next().value,
    description:   casual.text,
    price:         String(casual.double(0, 100)),
    thumbnail_url: casual.url,
    run_ids:       runIds,
    // $FlowFixMe: flow doesn't understand generators well
    object_id:     genNextObjectId.next().value,
    // $FlowFixMe: flow doesn't understand generators well
    product_id:    genProductId.next().value
  }
}

export const makeCouponSelection = (item: ?BasketItem): CouponSelection => ({
  code:    casual.word,
  amount:  String(casual.double(0, 1)),
  targets: item ? [item.id] : []
})

export const makeBasketResponse = (itemType: ?string): BasketResponse => {
  const item = makeItem(itemType)
  return {
    items:         [item],
    coupons:       [makeCouponSelection(item)],
    data_consents: [makeDataConsent()]
  }
}

export const makeProduct = (
  productType: string = PRODUCT_TYPE_COURSERUN
): Product => ({
  // $FlowFixMe
  id:           genProductId.next().value,
  product_type: productType
    ? productType
    : casual.random_element([PRODUCT_TYPE_COURSERUN, PRODUCT_TYPE_PROGRAM]),
  title:        casual.word,
  object_id:    casual.number,
  content_type: casual.number,
  text_id:      casual.word,
  created_on:   casual.moment.format(),
  updated_on:   casual.moment.format()
})

const genCompanyId = incrementer()
export const makeCompany = (): Company => ({
  // $FlowFixMe
  id:         genCompanyId.next().value,
  name:       casual.word,
  created_on: casual.moment.format(),
  updated_on: casual.moment.format()
})

const genCouponPaymentId = incrementer()
export const makeCouponPayment = (): CouponPayment => ({
  // $FlowFixMe
  id:         genCouponPaymentId.next().value,
  name:       casual.word,
  created_on: casual.moment.format(),
  updated_on: casual.moment.format()
})

const genCouponPaymentVersionId = incrementer()
export const makeCouponPaymentVersion = (
  isPromo: boolean = false
): CouponPaymentVersion => ({
  // $FlowFixMe
  id:                       genCouponPaymentVersionId.next().value,
  payment:                  makeCouponPayment(),
  tag:                      casual.word,
  automatic:                false,
  coupon_type:              isPromo ? "promo" : "single-use",
  num_coupon_codes:         casual.number,
  max_redemptions:          casual.number,
  max_redemptions_per_user: 1,
  amount:                   casual.random,
  activation_date:          casual.date,
  expiration_date:          casual.date,
  payment_type:             casual.random_element([
    "sales",
    "marketing",
    "credit_card",
    "purchase_order"
  ]),
  payment_transaction: casual.word,
  company:             casual.word,
  created_on:          casual.moment.format(),
  updated_on:          casual.moment.format()
})

const genBulkCouponPaymentId = incrementer()
export const makeBulkCouponPayment = (): BulkCouponPayment => ({
  // $FlowFixMe
  id:         genBulkCouponPaymentId.next().value,
  name:       casual.word,
  version:    makeCouponPaymentVersion(),
  products:   [makeProduct()],
  created_on: casual.moment.format(),
  updated_on: casual.moment.format()
})
