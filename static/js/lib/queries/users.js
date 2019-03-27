// @flow
import { nthArg, objOf } from "ramda"

import type { CurrentUser } from "../../flow/authTypes"

export const currentUserSelector = (state: any): ?CurrentUser =>
  state.entities.currentUser

// replace the previous state with the next state without merging
const nextState = nthArg(1)

// project the result into entities.currentUser
const transformCurrentUser = objOf("currentUser")

const updateResult = {
  currentUser: nextState
}

export default {
  currentUserQuery: () => ({
    url:       "/api/users/me",
    transform: transformCurrentUser,
    update:    updateResult
  })
}
