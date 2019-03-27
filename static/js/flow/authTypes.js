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

export type User = {
    id: number,
    username: string,
    email: string,
    name: string,
    created_on: string,
    updated_on: string
}

export type AnonymousUser = {
  is_anonymous: true,
  is_authenticated: false,
}

export type LoggedInUser = {
  is_anonymous: false,
  is_authenticated: true,
} & User

export type CurrentUser = AnonymousUser | LoggedInUser
