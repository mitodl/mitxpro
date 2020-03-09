// @flow
import React from "react"
import { assert } from "chai"
import { shallow } from "enzyme"

import {
  TextNotification,
  UnusedCouponNotification,
  B2BOrderStatusNotification
} from "."
import { routes } from "../../lib/urls"
import IntegrationTestHelper from "../../util/integration_test_helper"

describe("Notification component", () => {
  let helper, dismissStub

  beforeEach(() => {
    helper = new IntegrationTestHelper()
    dismissStub = helper.sandbox.stub()
  })

  afterEach(() => {
    helper.cleanup()
  })

  it("TextNotification", () => {
    const text = "Some text"
    const wrapper = shallow(
      <TextNotification text={"Some text"} dismiss={dismissStub} />
    )
    assert.equal(wrapper.text(), text)
  })

  it("UnusedCouponNotification", () => {
    const productId = 1,
      couponCode = "code"
    const wrapper = shallow(
      <UnusedCouponNotification
        productId={productId}
        couponCode={couponCode}
        dismiss={dismissStub}
      />
    )
    const link = wrapper.find("MixedLink")
    assert.isTrue(link.exists())
    assert.deepInclude(link.props(), {
      dest:      `${routes.checkout}?product=${productId}&code=${couponCode}`,
      onClick:   dismissStub,
      className: "alert-link"
    })
  })

  it("B2BOrderStatusNotification", () => {
    const wrapper = shallow(
      <B2BOrderStatusNotification dismiss={dismissStub} />
    )
    assert.equal(
      wrapper.text(),
      "Something went wrong. Please contact us at Customer Support."
    )
    const link = wrapper.find("a")
    assert.isTrue(link.exists())
    assert.equal(link.text(), "Customer Support")
    assert.deepInclude(link.props(), {
      href:      "https://xpro.zendesk.com/hc/en-us/requests/new",
      onClick:   dismissStub,
      className: "alert-link"
    })
  })
})
