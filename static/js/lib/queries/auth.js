// @flow
import { FLOW_LOGIN } from "../auth"

import type { RequestConfig } from "redux-query"

export default {
  loginEmailMutation: (email: string, next: ?string): RequestConfig => ({
    url:  "/api/login/email/",
    body: { email, next, flow: FLOW_LOGIN }
  }),

  loginPasswordMutation: (
    password: string,
    partialToken: string
  ): RequestConfig => ({
    url:  "/api/login/password/",
    body: { password, partial_token: partialToken, flow: FLOW_LOGIN }
  })
}
