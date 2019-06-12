// @flow
import { assert } from "chai"

import { userNotifications as notificationsReducer } from "./notifications"
import { ADD_USER_NOTIFICATION, REMOVE_USER_NOTIFICATION } from "../actions"
import { ALERT_TYPE_TEXT } from "../constants"

describe("notifications reducer", () => {
  it("should let you add and remove user notifications", () => {
    const messageId = "some-text-alert"
    const payload = {
      [messageId]: {
        type:  ALERT_TYPE_TEXT,
        props: {
          text: "some message"
        }
      }
    }

    let action = {
      type:    ADD_USER_NOTIFICATION,
      payload: payload,
      meta:    null
    }
    let resultState = notificationsReducer(undefined, action)
    assert.deepEqual(resultState, payload)

    action = {
      type:    REMOVE_USER_NOTIFICATION,
      payload: messageId,
      meta:    null
    }
    resultState = notificationsReducer(resultState, action)
    assert.deepEqual(notificationsReducer(resultState, action), {})
  })
})
