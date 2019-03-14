// @flow
import { combineReducers } from "redux"
import { entitiesReducer, queriesReducer } from "redux-query"

export default combineReducers<any, any>({
  entities: entitiesReducer,
  queries:  queriesReducer
})
