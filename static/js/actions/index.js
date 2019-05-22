// @flow
import { createAction } from "redux-actions"

export const ADD_USER_NOTIFICATION = "ADD_USER_NOTIFICATION"
export const addUserNotification = createAction(ADD_USER_NOTIFICATION)

export const REMOVE_USER_NOTIFICATION = "REMOVE_USER_NOTIFICATION"
export const removeUserNotification = createAction(REMOVE_USER_NOTIFICATION)
