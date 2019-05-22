// @flow
import { assert } from "chai"

import NotificationContainer, {
  NotificationContainer as InnerNotificationContainer
} from "./NotificationContainer"
import IntegrationTestHelper from "../util/integration_test_helper"

describe("NotificationContainer component", () => {
  const messages = ["some message", "some other message"]
  let helper, render

  beforeEach(() => {
    helper = new IntegrationTestHelper()
    render = helper.configureHOCRenderer(
      NotificationContainer,
      InnerNotificationContainer,
      {
        ui: {
          userNotifications: new Set()
        }
      },
      {}
    )
  })

  afterEach(() => {
    helper.cleanup()
  })

  it("has a link to login", async () => {
    const { inner } = await render({
      ui: {
        userNotifications: new Set(messages)
      }
    })
    const alerts = inner.find("Alert")
    assert.lengthOf(alerts, messages.length)
    assert.equal(alerts.at(0).prop("children"), messages[0])
    assert.equal(alerts.at(1).prop("children"), messages[1])
  })

  it("hides a message when it's dismissed, then removes it from global state", async () => {
    const delayMs = 5
    const { inner, wrapper } = await render(
      {
        ui: {
          userNotifications: new Set(messages)
        }
      },
      { messageRemoveDelayMs: delayMs }
    )
    const alert = inner.find("Alert").at(0)
    const timeoutPromise = alert.prop("toggle")()
    assert.deepEqual(inner.state(), {
      hiddenNotifications: new Set([messages[0]])
    })

    await timeoutPromise
    wrapper.update()
    assert.deepEqual(wrapper.prop("userNotifications"), new Set([messages[1]]))
    assert.deepEqual(inner.state(), { hiddenNotifications: new Set() })
  })
})
