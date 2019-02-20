// @flow
import { combineReducers } from "redux"
import type { Action } from "../flow/reduxTypes"
import { UPDATE_CHECKBOX } from "../actions"

export type CheckboxType = {
  checked: boolean
}

const INITIAL_CHECKBOX_STATE: CheckboxType = {
  checked: false
}

export const checkbox = (
  state: CheckboxType = INITIAL_CHECKBOX_STATE,
  action: Action<any, any>
): CheckboxType => {
  switch (action.type) {
  case UPDATE_CHECKBOX:
    return Object.assign({}, state, {
      checked: action.payload.checked
    })
  default:
    return state
  }
}

export default combineReducers({
  checkbox
})
