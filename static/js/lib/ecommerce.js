// @flow
import Decimal from "decimal.js-light"
import * as R from "ramda"
import { equals } from "ramda"
import moment from "moment"

import type {
  BasketItem,
  CouponSelection,
  ProductDetail,
  ProductMap,
  BulkCouponPayment
} from "../flow/ecommerceTypes"
import {
  COUPON_TYPE_PROMO,
  PRODUCT_TYPE_COURSERUN,
  PRODUCT_TYPE_PROGRAM
} from "../constants"
import type { CourseRun } from "../flow/courseTypes"

export const calculateDiscount = (
  item: BasketItem,
  coupon: ?CouponSelection
): Decimal => {
  if (coupon && coupon.targets.includes(item.id)) {
    return new Decimal(coupon.amount)
      .times(new Decimal(item.price))
      .toFixed(2, Decimal.ROUND_HALF_UP)
  }

  return new Decimal(0)
}

export const calculatePrice = (
  item: BasketItem,
  coupon: ?CouponSelection
): Decimal => new Decimal(item.price).minus(calculateDiscount(item, coupon))

export const formatPrice = (price: ?string | number | Decimal): string => {
  if (price === null || price === undefined) {
    return ""
  } else {
    let formattedPrice: Decimal = Decimal(price)

    if (formattedPrice.isInteger()) {
      formattedPrice = formattedPrice.toFixed(0)
    } else {
      formattedPrice = formattedPrice.toFixed(2, Decimal.ROUND_HALF_UP)
    }
    return `$${formattedPrice}`
  }
}

const formatDateForRun = (dateString: ?string) =>
  dateString ? moment(dateString).format("ll") : "?"

export const formatRunTitle = (run: ?CourseRun) =>
  run
    ? `${formatDateForRun(run.start_date)} - ${formatDateForRun(run.end_date)}`
    : ""

export const isPromo = equals(COUPON_TYPE_PROMO)

export const createProductMap = (
  bulkCouponPayments: Array<BulkCouponPayment>
): ProductMap =>
  R.compose(
    R.mergeRight({
      [PRODUCT_TYPE_PROGRAM]:   [],
      [PRODUCT_TYPE_COURSERUN]: []
    }),
    R.groupBy(R.prop("product_type")),
    R.uniqBy(R.prop("id")),
    R.flatten,
    R.pluck("products")
  )(bulkCouponPayments)

export const findRunInProduct = (product: ProductDetail): ?CourseRun => {
  if (product.product_type !== PRODUCT_TYPE_COURSERUN) {
    // Calling functions are responsible for checking this
    throw new Error("Expected a run product")
  }

  const productVersion = product.latest_version
  const runId = productVersion.object_id

  for (const course of productVersion.courses) {
    for (const run of course.courseruns) {
      if (run.id === runId) {
        return run
      }
    }
  }

  // This should be prevented by the REST API
  return null
}
