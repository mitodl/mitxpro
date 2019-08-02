// @flow
import { pathOr, objOf } from "ramda"

import { getCookie } from "../api"

import type {
  B2BOrderStatus,
  BasketResponse,
  BulkCheckoutPayload,
  Company,
  CouponPaymentVersion,
  ProductDetail
} from "../../flow/ecommerceTypes"

const DEFAULT_POST_OPTIONS = {
  headers: {
    "X-CSRFTOKEN": getCookie("csrftoken")
  }
}

export default {
  checkoutMutation: () => ({
    queryKey: "checkoutMutation",
    url:      "/api/checkout/",
    update:   {
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
    queryKey: "basketMutation",
    url:      "/api/basket/",
    update:   {
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
    transform: (json: Array<ProductDetail>) => ({
      products: json
    }),
    update: {
      products: (prev: Array<ProductDetail>, next: Array<ProductDetail>) => next
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
    queryKey:  "couponsMutation",
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
  }),
  b2bCheckoutMutation: (payload: BulkCheckoutPayload) => ({
    queryKey: "b2bCheckoutMutation",
    url:      "/api/b2b/checkout/",
    update:   {
      b2b_checkout: () => null
    },
    body: {
      ...payload
    },
    options: {
      force: true,
      ...DEFAULT_POST_OPTIONS
    }
  }),
  b2bOrderStatus: (orderHash: string) => ({
    queryKey:  "b2bOrderStatus",
    url:       `/api/b2b/orders/${orderHash}/status/`,
    transform: (json: B2BOrderStatus) => ({
      b2b_order_status: json
    }),
    update: {
      b2b_order_status: (prev: B2BOrderStatus, next: B2BOrderStatus) => next
    }
  })
}
