// @flow
import { pathOr, nthArg } from "ramda"

import { FLOW_LOGIN, FLOW_REGISTER } from "../auth"

import { getCookie } from "../api"

import type {
  AuthResponse,
  LegalAddress,
  ProfileForm
} from "../../flow/authTypes"

import type { updateEmailResponse } from "../../flow/authTypes"

export const authSelector = (state: any) => state.entities.auth

export const updateEmailSelector = pathOr(null, ["entities", "updateEmail"])

// uses the next piece of state which is the second argument
const nextState = nthArg(1)

const DEFAULT_OPTIONS = {
  transform: (auth: AuthResponse) => ({ auth }),
  update:    {
    auth: nextState
  },
  options: {
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
    profileData: ProfileForm,
    partialToken: string
  ) => ({
    ...DEFAULT_OPTIONS,
    url:  "/api/register/extra/",
    body: {
      flow:          FLOW_REGISTER,
      partial_token: partialToken,
      ...profileData.profile
    }
  }),

  forgotPasswordMutation: (email: string) => ({
    url:     "/api/password_reset/",
    body:    { email },
    options: {
      method:  "POST",
      headers: {
        "X-CSRFTOKEN": getCookie("csrftoken")
      }
    }
  }),

  changePasswordMutation: (oldPassword: string, newPassword: string) => ({
    url:     "/api/set_password/",
    options: {
      headers: {
        "X-CSRFTOKEN": getCookie("csrftoken")
      }
    },
    body: {
      current_password: oldPassword,
      new_password:     newPassword
    }
  }),

  forgotPasswordConfirmMutation: (
    newPassword: string,
    reNewPassword: string,
    token: string,
    uid: string
  ) => ({
    url:  "/api/password_reset/confirm/",
    body: {
      new_password:    newPassword,
      re_new_password: reNewPassword,
      token,
      uid
    },
    options: {
      method:  "POST",
      headers: {
        "X-CSRFTOKEN": getCookie("csrftoken")
      }
    }
  }),

  changeEmailMutation: (newEmail: string, password: string) => ({
    url:     "/api/change-emails/",
    options: {
      method:  "POST",
      headers: {
        "X-CSRFTOKEN": getCookie("csrftoken")
      }
    },
    body: {
      new_email: newEmail,
      password:  password
    }
  }),

  confirmEmailMutation: (code: string) => ({
    queryKey:  "updateEmail",
    url:       `/api/change-emails/${code}/`,
    transform: (json: updateEmailResponse) => ({
      updateEmail: json
    }),
    update: {
      updateEmail: (prev: updateEmailResponse, next: updateEmailResponse) =>
        next
    },
    options: {
      method:  "PATCH",
      headers: {
        "X-CSRFTOKEN": getCookie("csrftoken")
      }
    },
    body: {
      confirmed: true
    }
  })
}
