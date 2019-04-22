// @flow
import { pathOr, objOf } from "ramda"

import { getCookie } from "../api"

import type {
  BasketResponse,
  Company,
  CouponPaymentVersion,
  Product
} from "../../flow/ecommerceTypes"

const DEFAULT_POST_OPTIONS = {
  headers: {
    "X-CSRFTOKEN": getCookie("csrftoken")
  }
}

export default {
  checkoutMutation: () => ({
    url:    "/api/checkout/",
    update: {
      checkout: () => null
    },
    options: {
      force: true,
      ...DEFAULT_POST_OPTIONS
    }
  }),
  basketQuery: () => ({
    url:       "/api/basket/",
    transform: (json: BasketResponse) => ({
      basket: json
    }),
    update: {
      basket: (prev: BasketResponse, next: BasketResponse) => next
    }
  }),
  basketMutation: (payload: BasketResponse) => ({
    url:    "/api/basket/",
    update: {
      basket: (prev: BasketResponse, next: BasketResponse) => next
    },
    transform: (json: BasketResponse) => ({
      basket: json
    }),
    body: {
      ...payload
    },
    options: {
      method: "PATCH",
      force:  true,
      ...DEFAULT_POST_OPTIONS
    }
  }),
  productsSelector: pathOr(null, ["entities", "products"]),
  productsQuery:    () => ({
    url:       "/api/products/",
    transform: (json: Array<Product>) => ({
      products: json
    }),
    update: {
      products: (prev: Array<Product>, next: Array<Product>) => next
    }
  }),
  companiesSelector: pathOr(null, ["entities", "companies"]),
  companiesQuery:    () => ({
    url:       "/api/companies/",
    transform: (json: Array<Company>) => objOf("companies", json),
    update:    {
      companies: (prev: Array<Company>, next: Array<Company>) => next
    }
  }),
  couponsSelector: pathOr(null, ["entities", "coupons"]),
  couponsMutation: (coupon: Object) => ({
    url:       "/api/coupons/",
    body:      coupon,
    transform: (coupon: CouponPaymentVersion) => ({
      coupons: {
        [coupon.id]: coupon
      }
    }),
    update: {
      coupons: (
        prevCoupons: { [string]: CouponPaymentVersion },
        nextCoupons: { [string]: CouponPaymentVersion }
      ) => ({
        ...prevCoupons,
        ...nextCoupons
      })
    },
    options: {
      ...DEFAULT_POST_OPTIONS
    }
  })
}
