// @flow
import { assert } from "chai"
import sinon from "sinon"
import { mergeRight } from "ramda"

import App, { App as InnerApp } from "./App"
import { routes } from "../lib/urls"
import IntegrationTestHelper from "../util/integration_test_helper"
import { makeUser, makeUnusedCoupon } from "../factories/user"
import { ALERT_TYPE_UNUSED_COUPON } from "../constants"

describe("Top-level App", () => {
  let helper, renderPage

  beforeEach(() => {
    helper = new IntegrationTestHelper()
    renderPage = helper.configureHOCRenderer(
      App,
      InnerApp,
      {},
      {
        match:    { url: routes.root },
        location: {
          pathname: routes.root
        }
      }
    )
  })

  afterEach(() => {
    helper.cleanup()
  })

  it("fetches user data on load and initially renders an empty element", async () => {
    const { inner } = await renderPage()

    assert.notExists(inner.find(".app").prop("children"))
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
        "unused-coupon-0": {
          type:  ALERT_TYPE_UNUSED_COUPON,
          props: {
            productId:   unusedCoupon.product_id,
            productName: unusedCoupon.product_name,
            couponCode:  unusedCoupon.coupon_code
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

    it("is triggered if the user changes from the checkout page to another page", async () => {
      let state
      const { inner, store } = await renderPage(
        {},
        {
          location: { pathname: routes.checkout }
        }
      )

      inner.setProps({ currentUser: userWithUnusedCoupons })
      state = store.getState()
      assert.deepEqual(state.ui.userNotifications, {})

      inner.setProps({ location: { pathname: routes.dashboard } })
      state = store.getState()
      assert.deepEqual(state.ui.userNotifications, expectedNotificationState)
    })
  })

  describe("unused coupons alert", () => {
    let userWithUnusedCoupons,
      unusedCoupon,
      unusedCoupon1,
      unusedCoupon2,
      expectedNotificationState

    beforeEach(() => {
      unusedCoupon = makeUnusedCoupon()
      unusedCoupon1 = makeUnusedCoupon()
      unusedCoupon2 = makeUnusedCoupon()
      userWithUnusedCoupons = mergeRight(makeUser(), {
        unused_coupons: [unusedCoupon, unusedCoupon1, unusedCoupon2]
      })
      expectedNotificationState = {
        "unused-coupon-0": {
          type:  ALERT_TYPE_UNUSED_COUPON,
          props: {
            productId:   unusedCoupon.product_id,
            productName: unusedCoupon.product_name,
            couponCode:  unusedCoupon.coupon_code
          }
        },
        "unused-coupon-1": {
          type:  ALERT_TYPE_UNUSED_COUPON,
          props: {
            productId:   unusedCoupon1.product_id,
            productName: unusedCoupon1.product_name,
            couponCode:  unusedCoupon1.coupon_code
          }
        },
        "unused-coupon-2": {
          type:  ALERT_TYPE_UNUSED_COUPON,
          props: {
            productId:   unusedCoupon2.product_id,
            productName: unusedCoupon2.product_name,
            couponCode:  unusedCoupon2.coupon_code
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

    it("is triggered if the user changes from the checkout page to another page", async () => {
      let state
      const { inner, store } = await renderPage(
        {},
        {
          location: { pathname: routes.checkout }
        }
      )

      inner.setProps({ currentUser: userWithUnusedCoupons })
      state = store.getState()
      assert.deepEqual(state.ui.userNotifications, {})

      inner.setProps({ location: { pathname: routes.dashboard } })
      state = store.getState()
      assert.deepEqual(state.ui.userNotifications, expectedNotificationState)
    })
  })
})
