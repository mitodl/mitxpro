// @flow
import { pathOr } from "ramda"

import { nextState } from "./util"
import { getCookie } from "../api"
import { objectToFormData } from "../util"
import { createProductMap } from "../ecommerce"

import type { BulkCouponPaymentsResponse } from "../../flow/ecommerceTypes"

export default {
  bulkCouponPaymentsSelector: pathOr(null, ["entities", "bulkCouponPayments"]),
  bulkCouponProductsSelector: pathOr(null, ["entities", "bulkCouponProducts"]),
  bulkCouponPaymentsQuery:    () => ({
    url:       "/api/bulk_coupons/",
    transform: (json: BulkCouponPaymentsResponse) => ({
      bulkCouponProducts: createProductMap(json),
      bulkCouponPayments: json
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
      force:   true,
      headers: {
        "X-CSRFTOKEN": getCookie("csrftoken")
      }
    }
  })
}
