// @flow
import casual from "casual-browserify"

import { incrementer } from "../lib/util"

import type {
  AnonymousUser,
  LoggedInUser,
  UnusedCoupon
} from "../flow/authTypes"

const incr = incrementer()

export const makeAnonymousUser = (): AnonymousUser => ({
  is_anonymous:     true,
  is_authenticated: false
})

export const makeUnusedCoupon = (): UnusedCoupon => ({
  // $FlowFixMe: Flow thinks incr.next().value may be undefined, but it won't ever be
  product_id:      incr.next().value,
  coupon_code:     casual.word,
  expiration_date: casual.moment.format()
})

export const makeUser = (username: ?string): LoggedInUser => ({
  // $FlowFixMe: Flow thinks incr.next().value may be undefined, but it won't ever be
  id:               incr.next().value,
  // $FlowFixMe: Flow thinks incr.next().value may be undefined, but it won't ever be
  username:         username || `${casual.word}_${incr.next().value}`,
  email:            casual.email,
  name:             casual.full_name,
  is_anonymous:     false,
  is_authenticated: true,
  created_on:       casual.moment.format(),
  updated_on:       casual.moment.format(),
  profile:          {
    gender:            "f",
    birth_year:        1980,
    company:           casual.company_name,
    company_size:      99,
    industry:          "",
    job_title:         casual.word,
    job_function:      "",
    leadership_level:  "",
    years_experience:  20,
    highest_education: "Doctorate"
  },
  legal_address: {
    street_address:     [casual.street],
    first_name:         casual.first_name,
    last_name:          casual.last_name,
    city:               casual.city,
    state_or_territory: "US-MA",
    country:            "US",
    postal_code:        "02090"
  },
  unused_coupons: []
})

export const makeCountries = () => [
  {
    code:   "US",
    name:   "United States",
    states: [
      { code: "US-CO", name: "Colorado" },
      { code: "US-MA", name: "Massachusetts" }
    ]
  },
  {
    code:   "CA",
    name:   "Canada",
    states: [
      { code: "CA-QC", name: "Quebec" },
      { code: "CA-NS", name: "Nova Scotia" }
    ]
  },
  { code: "FR", name: "France", states: [] },
  { code: "GB", name: "United Kingdom", states: [] }
]
