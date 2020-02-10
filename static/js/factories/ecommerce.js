// @flow
import casual from "casual-browserify"
import { range } from "ramda"
import Decimal from "decimal.js-light"

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
  ProductDetail,
  B2BOrderStatus,
  B2BCouponStatusResponse
} from "../flow/ecommerceTypes"
import type { BaseCourseRun, Program } from "../flow/courseTypes"
import { PRODUCT_TYPE_COURSERUN, PRODUCT_TYPE_PROGRAM } from "../constants"

const genBasketItemId = incrementer()
const genBasketItemObjectId = incrementer()
const genProductId = incrementer()
const genDataConsentUserId = incrementer()

export const makeDataConsent = (): DataConsentUser => ({
  // $FlowFixMe: flow doesn't understand generators well
  id:           genDataConsentUserId.next().value,
  company:      makeCompany(),
  consent_date: casual.moment.format(),
  consent_text: casual.text
})

export const makeItem = (
  productType: ?string,
  readableId: ?string
): BasketItem => {
  const basketItemType =
    productType ||
    casual.random_element([PRODUCT_TYPE_COURSERUN, PRODUCT_TYPE_PROGRAM])
  const numCourses = basketItemType === PRODUCT_TYPE_COURSERUN ? 1 : 4
  const courses = range(0, numCourses).map(() => makeCourse())
  const runIds = courses.map(course => course.courseruns[0].id)
  let productReadableId = casual.text
  if (readableId) {
    productReadableId = readableId
  }

  let objectId = genBasketItemObjectId.next().value
  if (productType === PRODUCT_TYPE_COURSERUN) {
    const choices = []
    for (const course of courses) {
      for (const run of course.courseruns) {
        choices.push(run.id)
      }
    }
    objectId = casual.random_element(choices)
  }

  return {
    type:          basketItemType,
    courses:       courses,
    // $FlowFixMe: flow doesn't understand generators well
    id:            genBasketItemId.next().value,
    description:   casual.text,
    content_title: casual.text,
    price:         String(casual.double(0, 100)),
    thumbnail_url: casual.url,
    run_ids:       runIds,
    // $FlowFixMe: flow doesn't understand generators well
    object_id:     objectId,
    // $FlowFixMe: flow doesn't understand generators well
    product_id:    genProductId.next().value,
    readable_id:   productReadableId,
    created_on:    casual.moment.format(),
    start_date:    casual.moment.format()
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
  productType: string = PRODUCT_TYPE_COURSERUN,
  readableId: string = casual.text
): ProductDetail => ({
  // $FlowFixMe
  id:                   genProductId.next().value,
  title:                casual.word,
  product_type:         productType,
  visible_in_bulk_form: casual.boolean,
  latest_version:       makeItem(productType, readableId)
})

export const makeCourseRunOrProgram = (
  productType: string = PRODUCT_TYPE_COURSERUN,
  courseWareId: ?string
): [BaseCourseRun | Program] => {
  // $FlowFixMe
  const product = {}
  product.id = genProductId.next().value
  product.title = casual.title
  product.description = casual.description
  product.thumbnail_url = casual.url
  if (productType === PRODUCT_TYPE_COURSERUN) {
    if (courseWareId) {
      product.courseware_id = courseWareId
    } else {
      product.courseware_id = casual.string.replace(/ /g, "+")
    }
  } else {
    product.readable_id = casual.string.replace(/ /g, "+")
  }
  return product
}

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
  num_coupon_codes:         casual.integer(0, 15),
  max_redemptions:          casual.integer(0, 15),
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

export const makeB2BOrderStatus = (): B2BOrderStatus => {
  const itemPrice = new Decimal(casual.integer(0, 1000))
  const numSeats = casual.integer(0, 1000)
  const contractNumber = casual.integer(1000, 5000)
  const discount = casual.coin_flip
    ? new Decimal(casual.double(0, 1)).times(numSeats).times(itemPrice)
    : null
  let totalPrice = itemPrice.times(numSeats)
  if (discount !== null) {
    totalPrice = totalPrice.minus(discount)
  }

  return {
    status:          casual.random_element(["fulfilled", "created"]),
    num_seats:       numSeats,
    item_price:      String(itemPrice),
    total_price:     String(totalPrice),
    email:           casual.email,
    product_version: makeProduct().latest_version,
    discount:        discount !== null ? String(discount) : null,
    contract_number: contractNumber
  }
}

export const makeB2BCouponStatus = (): B2BCouponStatusResponse => ({
  code:             casual.text,
  product_id:       makeProduct().id,
  discount_percent: new Decimal(casual.integer(0, 100)).dividedBy(100)
})
