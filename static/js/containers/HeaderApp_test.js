// @flow
import { assert } from "chai"
import sinon from "sinon"
import { mergeRight } from "ramda"

import HeaderApp, { HeaderApp as InnerHeaderApp } from "./HeaderApp"
import IntegrationTestHelper from "../util/integration_test_helper"
import { makeUser, makeUnusedCoupon } from "../factories/user"
import { ALERT_TYPE_UNUSED_COUPON } from "../constants"

describe("Top-level HeaderApp", () => {
  let helper, renderPage

  beforeEach(() => {
    helper = new IntegrationTestHelper()
    renderPage = helper.configureHOCRenderer(HeaderApp, InnerHeaderApp, {}, {})
  })

  afterEach(() => {
    helper.cleanup()
  })

  it("fetches user data on load and initially renders an empty element", async () => {
    const { inner } = await renderPage()

    assert.notExists(inner.find("div").prop("children"))
    sinon.assert.calledWith(helper.handleRequestStub, "/api/users/me", "GET")
  })

  describe("unused coupon alert", () => {
    let userWithUnusedCoupons, unusedCoupon, expectedNotificationState

    beforeEach(() => {
      unusedCoupon = makeUnusedCoupon()
      userWithUnusedCoupons = mergeRight(makeUser(), {
        unused_coupons: [unusedCoupon]
      })
      expectedNotificationState = {
        "unused-coupon": {
          type:  ALERT_TYPE_UNUSED_COUPON,
          props: {
            productId:  unusedCoupon.product_id,
            couponCode: unusedCoupon.coupon_code
          }
        }
      }
    })

    it("is triggered if the user is loaded and has unused coupons", async () => {
      const { inner, store } = await renderPage()

      inner.setProps({ currentUser: userWithUnusedCoupons })

      const { ui } = store.getState()
      assert.deepEqual(ui.userNotifications, expectedNotificationState)
    })
  })
})
