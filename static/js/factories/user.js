// @flow
import casual from "casual-browserify"

import { incrementer } from "../lib/util"

import type { AnonymousUser, LoggedInUser } from "../flow/authTypes"

const incr = incrementer()

export const makeAnonymousUser = (): AnonymousUser => ({
  is_anonymous:     true,
  is_authenticated: false
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
  profile:          null,
  legal_address:    null
})
