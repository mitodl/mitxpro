// @flow
import { nthArg } from "ramda"
import { FLOW_LOGIN, FLOW_REGISTER } from "../auth"

import type {
  AuthResponse,
  AuthResponseRaw,
  LegalAddress,
  UserProfile
} from "../../flow/authTypes"

export const authSelector = (state: any) => state.entities.auth

const transformAuthResult = (
  result: AuthResponseRaw
): { auth: AuthResponse } => ({
  auth: {
    partialToken: result.partial_token,
    flow:         result.flow,
    state:        result.state,
    errors:       result.errors,
    redirectUrl:  result.redirect_url,
    extraData:    {
      name: result.extra_data.name
    }
  }
})

// replace the previous state with the next state without merging
const nextState = nthArg(1)

const updateAuthResult = {
  auth: nextState
}

const DEFAULT_OPTIONS = {
  transform: transformAuthResult,
  update:    updateAuthResult,
  options:   {
    method: "POST"
  }
}

export default {
  loginEmailMutation: (email: string, next: ?string) => ({
    ...DEFAULT_OPTIONS,
    url:  "/api/login/email/",
    body: { email, next, flow: FLOW_LOGIN }
  }),

  loginPasswordMutation: (password: string, partialToken: string) => ({
    ...DEFAULT_OPTIONS,
    url:  "/api/login/password/",
    body: { password, partial_token: partialToken, flow: FLOW_LOGIN }
  }),

  registerEmailMutation: (
    email: string,
    recaptcha: ?string,
    next: ?string
  ) => ({
    ...DEFAULT_OPTIONS,
    url:  "/api/register/email/",
    body: { email, recaptcha, next, flow: FLOW_REGISTER }
  }),

  registerConfirmEmailMutation: (code: string, partialToken: string) => ({
    ...DEFAULT_OPTIONS,
    url:  "/api/register/confirm/",
    body: {
      verification_code: code,
      partial_token:     partialToken,
      flow:              FLOW_REGISTER
    }
  }),

  registerDetailsMutation: (
    name: string,
    password: string,
    legalAddress: LegalAddress,
    partialToken: string
  ) => ({
    ...DEFAULT_OPTIONS,
    url:  "/api/register/details/",
    body: {
      name,
      password,
      legal_address: legalAddress,
      flow:          FLOW_REGISTER,
      partial_token: partialToken
    }
  }),

  registerExtraDetailsMutation: (
    profileData: UserProfile,
    partialToken: string
  ) => ({
    ...DEFAULT_OPTIONS,
    url:  "/api/register/extra/",
    body: {
      flow:          FLOW_REGISTER,
      partial_token: partialToken,
      ...profileData
    }
  })
}
