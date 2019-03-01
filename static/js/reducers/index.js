// @flow
import { combineReducers } from "redux"
import { entitiesReducer, queriesReducer } from "redux-query"

import { UPDATE_CHECKBOX } from "../actions"

import type { Action } from "../flow/reduxTypes"

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
  checkbox: checkbox,
  entities: entitiesReducer,
  queries:  queriesReducer
})
