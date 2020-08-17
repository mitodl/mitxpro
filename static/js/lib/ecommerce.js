// @flow
import Decimal from "decimal.js-light"
import * as R from "ramda"
import { equals } from "ramda"
import moment from "moment"

import type {
  BasketItem,
  CouponSelection,
  Product,
  ProductMap,
  BulkCouponPayment
} from "../flow/ecommerceTypes"
import {
  COUPON_TYPE_PROMO,
  PRODUCT_TYPE_COURSERUN,
  PRODUCT_TYPE_PROGRAM
} from "../constants"
import type { Course, CourseRun } from "../flow/courseTypes"

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

const determinePreselectRunTag = (
  item: BasketItem,
  preselectId: number = 0
): ?string => {
  if (preselectId && item.courses.length > 0) {
    const matchingPreselectRun = item.courses[0].courseruns.find(
      run => run.id === preselectId
    )
    if (matchingPreselectRun && matchingPreselectRun.run_tag) {
      return matchingPreselectRun.run_tag
    } else {
      return null
    }
  }
  if (item.run_tag) {
    return item.run_tag
  }
  return null
}

export const calcSelectedRunIds = (
  item: BasketItem,
  preselectId: number = 0
): { [number]: number } => {
  if (item.type === PRODUCT_TYPE_COURSERUN) {
    const course = item.courses[0]
    return {
      [course.id]: item.object_id
    }
  }

  const preselectRunTag = determinePreselectRunTag(item, preselectId)
  if (!preselectRunTag) {
    return {}
  }

  const numCourses = item.courses.length
  const courseRunSelectionMap = {}
  for (const course of item.courses) {
    const matchingRun = course.courseruns.find(
      run => run.run_tag === preselectRunTag
    )
    if (matchingRun) {
      courseRunSelectionMap[course.id] = matchingRun.id
    }
  }
  return Object.keys(courseRunSelectionMap).length === numCourses
    ? courseRunSelectionMap
    : {}
}

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

export const formatCoursewareDate = (dateString: ?string) =>
  dateString ? moment(dateString).format("ll") : "?"

export const formatRunTitle = (run: ?CourseRun) =>
  run
    ? `${formatCoursewareDate(run.start_date)} - ${formatCoursewareDate(
      run.end_date
    )}`
    : ""

export const isPromo = equals(COUPON_TYPE_PROMO)

export const findProductById = (
  products: Array<Product>,
  id: number | string
): ?Product => {
  if (isNaN(id)) {
    return products.find(product => product.latest_version.readable_id === id)
  } else {
    return products.find(product => product.id === parseInt(id))
  }
}

export const findRunInProduct = (product: Product): [?CourseRun, ?Course] => {
  if (product.product_type !== PRODUCT_TYPE_COURSERUN) {
    // Calling functions are responsible for checking this
    throw new Error("Expected a run product")
  }

  const productVersion = product.latest_version
  const runId = productVersion.object_id

  for (const course of productVersion.courses) {
    for (const run of course.courseruns) {
      if (run.id === runId) {
        return [run, course]
      }
    }
  }

  // This should be prevented by the REST API
  return [null, null]
}
