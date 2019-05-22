// @flow
import { ADD_USER_NOTIFICATION, REMOVE_USER_NOTIFICATION } from "../actions"
import { newSetWith, newSetWithout } from "../lib/util"

import type { Action } from "../flow/reduxTypes"

export type UIState = {
  userNotifications: Set<string>
}

export const INITIAL_UI_STATE: UIState = {
  userNotifications: new Set()
}

export const ui = (
  state: UIState = INITIAL_UI_STATE,
  action: Action<any, null>
): UIState => {
  switch (action.type) {
  case ADD_USER_NOTIFICATION:
    return {
      ...state,
      userNotifications: newSetWith(state.userNotifications, action.payload)
    }
  case REMOVE_USER_NOTIFICATION:
    return {
      ...state,
      userNotifications: newSetWithout(
        state.userNotifications,
        action.payload
      )
    }
  }
  return state
}
