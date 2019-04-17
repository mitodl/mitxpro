// @flow
import Decimal from "decimal.js-light"

import type { BasketItem, Coupon } from "../flow/ecommerceTypes"

export const calculateDiscount = (
  item: BasketItem,
  coupon: ?Coupon
): Decimal => {
  if (coupon && coupon.targets.includes(item.id)) {
    return new Decimal(coupon.amount)
      .times(new Decimal(item.price))
      .toFixed(2, Decimal.ROUND_HALF_UP)
  }

  return new Decimal(0)
}

export const calculatePrice = (item: BasketItem, coupon: ?Coupon): Decimal =>
  new Decimal(item.price).minus(calculateDiscount(item, coupon))

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
