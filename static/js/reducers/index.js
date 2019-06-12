// @flow
import { combineReducers } from "redux"
import { entitiesReducer, queriesReducer } from "redux-query"

import ui from "./ui"

export default combineReducers<any, any>({
  entities: entitiesReducer,
  queries:  queriesReducer,
  ui
})
