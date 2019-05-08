// @flow
/* global SETTINGS:false */
import qs from "query-string"

import { routes } from "../lib/urls"

export const FLOW_REGISTER = "register"
export const FLOW_LOGIN = "login"

export const STATE_ERROR = "error"
export const STATE_SUCCESS = "success"
export const STATE_INACTIVE = "inactive"
export const STATE_INVALID_EMAIL = "invalid-email"

export const STATE_LOGIN_EMAIL = "login/email"
export const STATE_LOGIN_PASSWORD = "login/password"
export const STATE_LOGIN_PROVIDER = "login/provider"

export const STATE_REGISTER_EMAIL = "register/email"
export const STATE_REGISTER_CONFIRM_SENT = "register/confirm-sent"
export const STATE_REGISTER_CONFIRM = "register/confirm"
export const STATE_REGISTER_DETAILS = "register/details"
export const STATE_REGISTER_EXTRA_DETAILS = "register/extra"

export const generateLoginRedirectUrl = () => {
  const { pathname, search, hash } = window.location

  const next = `${pathname}${search}${hash}`
  return `${routes.login.begin}?${qs.stringify({ next })}`
}
