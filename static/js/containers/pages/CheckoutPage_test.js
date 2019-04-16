// @flow
import { assert } from "chai"
import sinon from "sinon"

import CheckoutPage, { CheckoutPage as InnerCheckoutPage } from "./CheckoutPage"
import * as formFuncs from "../../lib/form"
import IntegrationTestHelper from "../../util/integration_test_helper"
import { makeBasketResponse, makeCoupon } from "../../factories/ecommerce"
import {
  calculateDiscount,
  calculatePrice,
  formatPrice
} from "../../lib/ecommerce"

describe("CheckoutPage", () => {
  let helper, renderPage, basket

  beforeEach(() => {
    basket = makeBasketResponse()

    helper = new IntegrationTestHelper()
    renderPage = helper.configureHOCRenderer(
      CheckoutPage,
      InnerCheckoutPage,
      {
        entities: {
          basket
        }
      },
      {}
    )
  })

  afterEach(() => {
    helper.cleanup()
  })
  ;[true, false].forEach(hasCoupon => {
    it(`shows your basket ${
      hasCoupon ? "with" : "without"
    } a coupon`, async () => {
      const basketItem = basket.items[0]
      const coupon = makeCoupon()
      basket.coupons = [coupon]
      if (hasCoupon) {
        coupon.targets = [basketItem.id]
      } else {
        coupon.targets = [-123]
      }
      const { inner } = await renderPage()

      const courseRow = inner.find(".course-row")
      assert.equal(courseRow.find("img").prop("src"), basketItem.thumbnail_url)
      assert.equal(courseRow.find("img").prop("alt"), basketItem.description)
      assert.equal(
        inner.find(".price-row").text(),
        `Price ${formatPrice(basketItem.price)}`
      )

      if (hasCoupon) {
        assert.equal(
          inner.find(".discount-row").text(),
          `Discount applied ${formatPrice(
            calculateDiscount(basketItem, coupon)
          )}`
        )
      } else {
        assert.isFalse(inner.find(".discount-row").exists())
      }

      assert.equal(
        inner.find(".total-row").text(),
        `Total ${formatPrice(calculatePrice(basketItem, coupon))}`
      )
    })
  })

  it("displays the coupon code", async () => {
    const { inner } = await renderPage()
    const couponCode = "a coupon code"
    inner.setState({
      couponCode
    })
    inner.update()
    assert.equal(inner.find(".coupon-code-row input").prop("value"), couponCode)
  })

  it("updates the coupon code", async () => {
    const { inner } = await renderPage()
    const couponCode = "a coupon code"
    const event = {
      target: {
        value: couponCode
      },
      preventDefault: helper.sandbox.stub()
    }
    inner.find(".coupon-code-row input").prop("onChange")(event)
    assert.equal(inner.state().couponCode, couponCode)
  })
  ;[true, false].forEach(hasCouponCode => {
    it(`${hasCouponCode ? "submits" : "clears"} the coupon code`, async () => {
      const { inner } = await renderPage()
      const couponCode = "code"
      inner.setState({
        couponCode: hasCouponCode ? couponCode : ""
      })

      inner.find("form").prop("onSubmit")({
        preventDefault: helper.sandbox.stub()
      })
      sinon.assert.calledWith(
        helper.handleRequestStub,
        "/api/basket/",
        "PATCH",
        {
          body:    { coupons: hasCouponCode ? [{ code: couponCode }] : [] },
          headers: {
            "X-CSRFTOKEN": null
          },
          credentials: undefined
        }
      )
    })
  })

  it("checks out", async () => {
    const { inner } = await renderPage()

    const url = "/api/checkout/"
    const payload = { pay: "load" }
    helper.handleRequestStub.returns({
      body: {
        url,
        payload
      }
    })
    const submitStub = helper.sandbox.stub()
    const form = document.createElement("form")
    // $FlowFixMe: need to overwrite this function to mock it
    form.submit = submitStub
    const createFormStub = helper.sandbox
      .stub(formFuncs, "createCyberSourceForm")
      .returns(form)
    await inner.find("button.checkout").prop("onClick")()
    sinon.assert.calledWith(createFormStub, url, payload)
    sinon.assert.calledWith(submitStub)
  })

  it("displays no items if there are none in the basket", async () => {
    basket.items = []
    const { inner } = await renderPage()
    assert.equal(inner.text(), "No item in basket")
  })
})
