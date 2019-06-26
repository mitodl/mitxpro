// @flow

// API response types
export type AuthStates =
  | "success"
  | "inactive"
  | "invalid-email"
  | "user-blocked"
  | "error"
  | "error-temporary"
  | "login/email"
  | "login/password"
  | "login/provider"
  | "register/email"
  | "register/confirm-sent"
  | "register/confirm"
  | "register/details"
  | "register/extra"

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
  redirect_url:  ?string,
  extraData: {
    name?: string
  }
}

export type LegalAddress = {
  first_name: string,
  last_name: string,
  street_address: Array<string>,
  country: string,
  state_or_territory?: string,
  postal_code?: string
}

export type UnusedCoupon = {
  coupon_code: string,
  product_id: number,
  expiration_date: string
}

export type Profile = {
  gender: string,
  birth_year: number,
  company: string,
  industry: ?string,
  job_title: string,
  job_function: ?string,
  years_experience: ?number,
  company_size: ?number,
  leadership_level: ?string
}

export type User = {
    id: number,
    username: string,
    email: string,
    name: string,
    created_on: string,
    updated_on: string,
    profile: ?Profile,
    legal_address: ?LegalAddress,
    unused_coupons: Array<UnusedCoupon>
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

export type StateOrTerritory = {
  name: string,
  code: string
}

export type Country = {
  name:   string,
  code:   string,
  states: Array<StateOrTerritory>
}

export type ProfileForm = {
  profile: Profile
}

export type UserProfileForm = {
    email: string,
    name: string,
    legal_address: ?LegalAddress,
    profile: ?Profile
}
