// @flow
import React from "react"
import { include } from "named-urls"
import { Redirect } from "react-router-dom"
import qs from "query-string"

export const getNextParam = (search: string) => qs.parse(search).next || "/"

export const routes = {
  root:      "/",
  catalog:   "/catalog/",
  dashboard: "/dashboard/",
  logout:    "/logout/",

  // authentication related routes
  login: include("/login/", {
    begin:    "",
    password: "password/",
    forgot:   include("forgot-password/", {
      begin:   "",
      confirm: "confirm/:uid/:token/"
    })
  }),

  register: include("/signup/", {
    begin:   "",
    confirm: "confirm/",
    details: "details/",
    error:   "error/",
    extra:   "extra/",
    denied:  "denied/"
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
  })
}

export const createRedirectTo = (path: string) => () => <Redirect to={path} />

export const RedirectToRegister = createRedirectTo(routes.register.begin)
