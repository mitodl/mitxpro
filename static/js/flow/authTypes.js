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

export type AuthResponse = {
  partial_token: ?string,
  flow:          AuthFlow,
  state:         AuthStates,
  errors:        Array<string>,
  redirect_url:  ?string,
  extra_data: {
    name?: string
  }
}
