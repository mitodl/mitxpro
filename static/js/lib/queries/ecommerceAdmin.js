// @flow
import { pathOr } from "ramda"

import { nextState } from "./util"
import { getCookie } from "../api"
import { objectToFormData } from "../util"

import type { BulkCouponPaymentsResponse } from "../../flow/ecommerceTypes"

export default {
  bulkCouponPaymentsSelector: pathOr(null, ["entities", "bulkCouponPayments"]),
  bulkCouponProductsSelector: pathOr(null, ["entities", "bulkCouponProducts"]),
  bulkCouponPaymentsQuery:    () => ({
    url:       "/api/bulk_coupons/",
    transform: (json: BulkCouponPaymentsResponse) => ({
      bulkCouponProducts: json.product_map,
      bulkCouponPayments: json.coupon_payments
    }),
    update: {
      bulkCouponProducts: nextState,
      bulkCouponPayments: nextState
    }
  }),
  bulkEnrollmentMutation: (
    usersFile: Object,
    productId: number,
    couponPaymentId: number
  ) => ({
    url:  "/api/bulk_enroll/",
    body: objectToFormData({
      users_file:        usersFile,
      product_id:        parseInt(productId),
      coupon_payment_id: parseInt(couponPaymentId)
    }),
    options: {
      method:  "POST",
      headers: {
        "X-CSRFTOKEN": getCookie("csrftoken")
      }
    }
  })
}
