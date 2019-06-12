// @flow
import { combineReducers } from "redux"

import { userNotifications } from "./notifications"

export default combineReducers<any, any>({
  userNotifications
})
