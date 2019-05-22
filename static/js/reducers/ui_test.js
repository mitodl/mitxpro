// @flow
import { assert } from "chai"

import IntegrationTestHelper from "../util/integration_test_helper"
import { ui as uiReducer } from "./ui"
import { ADD_USER_NOTIFICATION, REMOVE_USER_NOTIFICATION } from "../actions"

describe("ui reducer", () => {
  let helper

  beforeEach(() => {
    helper = new IntegrationTestHelper()
  })

  afterEach(() => {
    helper.cleanup()
  })

  it("should let you add and remove user notifications", () => {
    const message = "some message"

    let action = {
      type:    ADD_USER_NOTIFICATION,
      payload: message,
      meta:    null
    }
    let resultState = uiReducer(undefined, action)
    assert.deepEqual(resultState, { userNotifications: new Set([message]) })

    action = {
      type:    REMOVE_USER_NOTIFICATION,
      payload: message,
      meta:    null
    }
    resultState = uiReducer(resultState, action)
    assert.deepEqual(uiReducer(resultState, action), {
      userNotifications: new Set([])
    })
  })
})
