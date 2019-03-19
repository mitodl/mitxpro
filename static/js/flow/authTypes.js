// @flow

// API response types
export type AuthStates =
  | "success"
  | "inactive"
  | "error"
  | "login/email"
  | "login/password"
  | "login/provider"
  | "register/email"
  | "register/confirm-sent"
  | "register/confirm"
  | "register/details"

export type AuthFlow = "register" | "login"

export type AuthResponseRaw = {
  partial_token: ?string,
  flow:          AuthFlow,
  state:         AuthStates,
  errors:        Array<string>,
  redirect_url:  ?string,
  extra_data: {
    name?: string
  }
}

export type AuthResponse = {
  partialToken: ?string,
  flow:          AuthFlow,
  state:         AuthStates,
  errors:        Array<string>,
  redirectUrl:  ?string,
  extraData: {
    name?: string
  }
}
