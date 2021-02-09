// @flow
import { pathOr, objOf, nthArg } from "ramda"

import { getCookie } from "../api"

import type {
  B2BOrderStatus,
  BasketPayload,
  BasketResponse,
  B2BCheckoutPayload,
  Company,
  CouponPaymentVersion,
  Product,
  B2BCouponStatusPayload,
  B2BCouponStatusResponse,
  OrderReceiptResponse,
  ProgramRunDetail
} from "../../flow/ecommerceTypes"

// uses the next piece of state which is the second argument
const nextState = nthArg(1)

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
  basketMutation: (payload: BasketPayload) => ({
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
      ...DEFAULT_POST_OPTIONS
    }
  }),
  productsSelector: pathOr(null, ["entities", "products"]),
  productsQuery:    (productType?: string) => ({
    queryKey: "products",
    url:      "/api/products/",
    body:     {
      ...(productType ? { type: productType } : {})
    },
    transform: (json: Array<Product>) => ({
      products: json
    }),
    update: {
      products: nextState
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
  b2bCheckoutMutation: (payload: B2BCheckoutPayload) => ({
    queryKey: "b2bCheckoutMutation",
    url:      "/api/b2b/checkout/",
    update:   {
      b2b_checkout: () => null
    },
    body: {
      ...payload
    },
    options: {
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
  }),
  b2bCouponStatusSelector: pathOr(null, ["entities", "b2b_coupon_status"]),
  b2bCouponStatus:         (payload: B2BCouponStatusPayload) => ({
    queryKey:  "b2bCouponStatus",
    url:       "/api/b2b/coupon_status/",
    transform: (json: B2BCouponStatusPayload) => ({
      b2b_coupon_status: json
    }),
    update: {
      b2b_coupon_status: (
        prev: B2BCouponStatusResponse,
        next: B2BCouponStatusResponse
      ) => next
    },
    body:  payload,
    force: true
  }),
  orderReceiptSelector: pathOr(null, ["entities", "orderReceipt"]),
  orderReceipt:         (orderId: string) => ({
    queryKey:  "orderReceipt",
    url:       `/api/order_receipt/${orderId}/`,
    transform: (json: OrderReceiptResponse) => ({
      orderReceipt: json
    }),
    update: {
      orderReceipt: (prev: OrderReceiptResponse, next: OrderReceiptResponse) =>
        next
    }
  }),
  programRunsSelector: pathOr(null, ["entities", "programRuns"]),
  programRunsQuery:    (productId: string) => ({
    queryKey:  "programRuns",
    url:       `/api/products/${productId}/runs/`,
    transform: (json: [ProgramRunDetail]) => ({
      programRuns: json
    }),
    update: {
      programRuns: (prev: [ProgramRunDetail], next: [ProgramRunDetail]) => next
    },
    force: true
  })
}
