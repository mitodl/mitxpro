// @flow
import { assert } from "chai"
import { omit } from "ramda"

import NotificationContainer, {
  NotificationContainer as InnerNotificationContainer
} from "./NotificationContainer"
import { TextNotification, UnusedCouponNotification } from "./notifications"
import { ALERT_TYPE_TEXT, ALERT_TYPE_UNUSED_COUPON } from "../constants"
import IntegrationTestHelper from "../util/integration_test_helper"

describe("NotificationContainer component", () => {
  const messages = {
    message1: {
      type:  ALERT_TYPE_TEXT,
      props: { text: "derp" }
    },
    message2: {
      type:  ALERT_TYPE_UNUSED_COUPON,
      props: {
        productId:  1,
        couponCode: "code"
      }
    }
  }

  let helper, render

  beforeEach(() => {
    helper = new IntegrationTestHelper()
    render = helper.configureHOCRenderer(
      NotificationContainer,
      InnerNotificationContainer,
      {
        ui: {
          userNotifications: {}
        }
      },
      {}
    )
  })

  afterEach(() => {
    helper.cleanup()
  })

  it("shows notifications", async () => {
    const { inner } = await render({
      ui: {
        userNotifications: messages
      }
    })
    const alerts = inner.find("Alert")
    assert.lengthOf(alerts, Object.keys(messages).length)
    assert.equal(alerts.at(0).prop("children").type, TextNotification)
    assert.equal(alerts.at(1).prop("children").type, UnusedCouponNotification)
  })

  //
  ;[[undefined, "info"], ["danger", "danger"]].forEach(
    ([color, expectedColor]) => {
      it(`shows a ${expectedColor} color notification given a ${String(
        color
      )} color prop`, async () => {
        const { inner } = await render({
          ui: {
            userNotifications: {
              aMessage: {
                type:  ALERT_TYPE_TEXT,
                color: color,
                props: { text: "derp" }
              }
            }
          }
        })
        assert.equal(inner.find("Alert").prop("color"), expectedColor)
      })
    }
  )

  it("hides a message when it's dismissed, then removes it from global state", async () => {
    const delayMs = 5
    const { inner, wrapper } = await render(
      {
        ui: {
          userNotifications: messages
        }
      },
      { messageRemoveDelayMs: delayMs }
    )
    const alert = inner.find("Alert").at(0)
    const timeoutPromise = alert.prop("toggle")()
    assert.deepEqual(inner.state(), {
      hiddenNotifications: new Set(["message1"])
    })

    await timeoutPromise
    wrapper.update()
    assert.deepEqual(
      wrapper.prop("userNotifications"),
      omit(["message1"], messages)
    )
    assert.deepEqual(inner.state(), { hiddenNotifications: new Set() })
  })
})
