// @flow
import _ from "lodash"
import Decimal from "decimal.js-light"

import type { BasketItem, Coupon } from "../flow/ecommerceTypes"

export const calculateDiscount = (item: BasketItem, coupon: ?Coupon) => {
  if (coupon && coupon.targets.includes(item.id)) {
    const amount = parseFloat(coupon.amount)
    return amount * parseFloat(item.price)
  }

  return 0
}

export const calculatePrice = (item: BasketItem, coupon: ?Coupon): Decimal => {
  const discount = calculateDiscount(item, coupon)
  const discountedPrice = parseFloat(item.price) - discount
  return _.round(discountedPrice, 2)
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
