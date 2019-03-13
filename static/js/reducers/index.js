// @flow
import { combineReducers } from "redux"
import { entitiesReducer, queriesReducer } from "redux-query"

export default combineReducers({
  entities: entitiesReducer,
  queries:  queriesReducer
})
