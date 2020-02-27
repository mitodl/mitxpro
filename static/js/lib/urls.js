// @flow
import { include } from "named-urls"
import qs from "query-string"

export const getNextParam = (search: string) => qs.parse(search).next || "/"

export const bulkReceiptCsvUrl = (hash: string) =>
  `/api/b2b/orders/${hash}/codes/`
export const bulkAssignmentCsvUrl = (bulkEnrollmentId: number) =>
  `/api/bulk_assignments/${bulkEnrollmentId}/`

export const routes = {
  root:            "/",
  catalog:         "/catalog/",
  dashboard:       "/dashboard/",
  accountSettings: "/account-settings/",
  logout:          "/logout/",

  // authentication related routes
  login: include("/signin/", {
    begin:    "",
    password: "password/",
    forgot:   include("forgot-password/", {
      begin:   "",
      confirm: "confirm/:uid/:token/"
    })
  }),

  register: include("/create-account/", {
    begin:       "",
    confirm:     "confirm/",
    confirmSent: "confirm-sent/",
    details:     "details/",
    error:       "error/",
    extra:       "extra/",
    denied:      "denied/"
  }),

  profile: include("/profile/", {
    view:   "",
    update: "edit/"
  }),

  checkout: "/checkout/",

  ecommerceAdmin: include("/ecommerce/admin/", {
    index:      "",
    bulkEnroll: "enroll/",
    coupons:    "coupons/"
  }),

  ecommerceBulk: include("/ecommerce/bulk/", {
    bulkPurchase: "",
    receipt:      "receipt/"
  }),
  receipt: "receipt/:orderId/",

  account: include("/account/", {
    confirmEmail: "confirm-email"
  })
}
