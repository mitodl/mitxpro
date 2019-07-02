// @flow
import { assert } from "chai"
import sinon from "sinon"

import CheckoutPage, {
  calcSelectedRunIds,
  CheckoutPage as InnerCheckoutPage
} from "./CheckoutPage"

import { PRODUCT_TYPE_PROGRAM } from "../../constants"
import { makeBasketResponse } from "../../factories/ecommerce"
import * as formFuncs from "../../lib/form"
import IntegrationTestHelper from "../../util/integration_test_helper"

describe("CheckoutPage", () => {
  let helper, renderPage, basket

  beforeEach(() => {
    basket = makeBasketResponse(PRODUCT_TYPE_PROGRAM)

    helper = new IntegrationTestHelper()
    renderPage = helper.configureHOCRenderer(
      CheckoutPage,
      InnerCheckoutPage,
      {
        entities: {
          basket
        }
      },
      {
        location: {}
      }
    )
  })

  afterEach(() => {
    helper.cleanup()
  })

  //
  ;[true, false].forEach(hasError => {
    it(`updates the basket with a product id from the query parameter${
      hasError ? ", but an error is returned" : ""
    }`, async () => {
      const productId = 4567
      if (hasError) {
        helper.handleRequestStub.withArgs("/api/basket/", "PATCH").returns({
          status: 400,
          body:   {
            errors: "error"
          }
        })
      }
      const { inner } = await renderPage(
        {},
        {
          location: {
            search: `product=${productId}`
          }
        }
      )

      sinon.assert.calledWith(
        helper.handleRequestStub,
        "/api/basket/",
        "PATCH",
        {
          body:        { items: [{ product_id: productId }] },
          credentials: undefined,
          headers:     {
            "X-CSRFTOKEN": null
          }
        }
      )
      assert.equal(inner.state().errors, hasError ? "error" : null)
    })
  })

  it("shows the coupon code from the query parameter", async () => {
    const code = "xyzzy"
    const { inner } = await renderPage(
      {},
      {
        location: {
          search: `product=4567&code=${code}`
        }
      }
    )
    assert.equal(inner.find("CheckoutForm").prop("couponCode"), code)
  })

  it("submits the coupon code", async () => {})
  ;[true, false].forEach(hasCouponCode => {
    [true, false].forEach(hasError => {
      it(`tries to submit ${hasCouponCode ? "an empty " : ""}the coupon code${
        hasError ? " but receives an error message" : ""
      }`, async () => {
        const setFieldError = helper.sandbox.stub()
        const couponError = "coupon error"
        if (hasError) {
          helper.handleRequestStub.withArgs("/api/basket/", "PATCH").returns({
            status: 400,
            body:   {
              errors: {
                coupons: couponError
              }
            }
          })
        }
        const { inner } = await renderPage()
        const couponCode = hasCouponCode ? "xyz" : ""
        await inner.find("CheckoutForm").prop("submitCoupon")(
          couponCode,
          setFieldError
        )
        sinon.assert.calledWith(
          setFieldError,
          "coupons",
          hasError ? couponError : undefined
        )
      })
    })
  })

  //
  ;[true, false].forEach(hasDataConsent => {
    it(`checks out ${
      hasDataConsent ? "with" : "without"
    } data consent`, async () => {
      const { inner } = await renderPage()

      const url = "/api/checkout/"
      const payload = { pay: "load" }
      helper.handleRequestStub.withArgs("/api/checkout/", "POST").returns({
        body: {
          url,
          payload
        },
        status: 200
      })
      const submitStub = helper.sandbox.stub()
      const form = document.createElement("form")
      // $FlowFixMe: need to overwrite this function to mock it
      form.submit = submitStub
      const createFormStub = helper.sandbox
        .stub(formFuncs, "createCyberSourceForm")
        .returns(form)
      const values = { runs: {}, dataConsent: hasDataConsent }
      const actions = {
        setSubmitting: helper.sandbox.stub(),
        setErrors:     helper.sandbox.stub()
      }
      await inner.find("CheckoutForm").prop("onSubmit")(values, actions)
      sinon.assert.calledWith(createFormStub, url, payload)
      sinon.assert.calledWith(submitStub)
      sinon.assert.calledWith(
        helper.handleRequestStub,
        "/api/checkout/",
        "POST",
        {
          body:    undefined,
          headers: {
            "X-CSRFTOKEN": null
          },
          credentials: undefined
        }
      )

      const basketItem = basket.items[0]
      sinon.assert.calledWith(
        helper.handleRequestStub,
        "/api/basket/",
        "PATCH",
        {
          body: {
            items: [
              {
                product_id: basketItem.product_id,
                run_ids:    []
              }
            ],
            coupons:       [],
            data_consents: hasDataConsent ? [basket.data_consents[0].id] : []
          },
          headers: {
            "X-CSRFTOKEN": null
          },
          credentials: undefined
        }
      )
      sinon.assert.calledWith(actions.setSubmitting, false)
      sinon.assert.notCalled(actions.setErrors)
    })
  })

  it("checks out and redirects to a location instead of submitting a form", async () => {
    const { inner } = await renderPage()

    const url = "/a/b/c/"
    const payload = { pay: "load" }
    helper.handleRequestStub.withArgs("/api/checkout/", "POST").returns({
      body: {
        url,
        payload,
        method: "GET"
      },
      status: 200
    })
    const submitStub = helper.sandbox.stub()
    const form = document.createElement("form")
    // $FlowFixMe: need to overwrite this function to mock it
    form.submit = submitStub
    const actions = {
      setSubmitting: helper.sandbox.stub(),
      setErrors:     helper.sandbox.stub()
    }
    const values = { runs: {} }
    await inner.find("CheckoutForm").prop("onSubmit")(values, actions)

    const basketItem = basket.items[0]
    sinon.assert.calledWith(helper.handleRequestStub, "/api/basket/", "PATCH", {
      body: {
        items: [
          {
            product_id: basketItem.product_id,
            run_ids:    []
          }
        ],
        coupons:       [],
        data_consents: []
      },
      headers: {
        "X-CSRFTOKEN": null
      },
      credentials: undefined
    })
    sinon.assert.notCalled(actions.setErrors)
    sinon.assert.calledWith(actions.setSubmitting, false)
    assert.isTrue(window.location.toString().endsWith(url))
  })

  it("fails to check out because basket API failed to validate", async () => {
    const { inner } = await renderPage()
    const errors = ["something went wrong"]

    helper.handleRequestStub.withArgs("/api/basket/", "PATCH").returns({
      status: 400,
      body:   {
        errors
      }
    })
    const submitStub = helper.sandbox.stub()
    const form = document.createElement("form")
    // $FlowFixMe: need to overwrite this function to mock it
    form.submit = submitStub

    const runId = 123
    const values = {
      runs: {
        [basket.items[0].courses[0].id]: runId
      }
    }
    const actions = {
      setSubmitting: helper.sandbox.stub(),
      setErrors:     helper.sandbox.stub()
    }
    await inner.find("CheckoutForm").prop("onSubmit")(values, actions)
    sinon.assert.calledWith(actions.setErrors, errors)
    sinon.assert.calledWith(actions.setSubmitting, false)
    assert.equal(submitStub.callCount, 0)
    sinon.assert.notCalled(submitStub)
    sinon.assert.calledWith(helper.handleRequestStub, "/api/basket/", "PATCH", {
      body: {
        items:         [{ product_id: basket.items[0].product_id, run_ids: [runId] }],
        coupons:       [],
        data_consents: []
      },
      credentials: undefined,
      headers:     {
        "X-CSRFTOKEN": null
      }
    })
    assert.isFalse(helper.handleRequestStub.calledWith("/api/checkout/"))
  })
  ;[true, false].forEach(hasCoupon => {
    it(`fails to check out because checkout API failed to validate${
      hasCoupon ? " with a coupon" : ""
    }`, async () => {
      const { inner } = await renderPage()

      const errors = ["some error"]
      helper.handleRequestStub.withArgs("/api/checkout/", "POST").returns({
        status: 400,
        body:   {
          errors
        }
      })
      const submitStub = helper.sandbox.stub()
      const form = document.createElement("form")
      // $FlowFixMe: need to overwrite this function to mock it
      form.submit = submitStub
      const runId = 123
      const code = "code"
      const values = {
        runs: {
          [basket.items[0].courses[0].id]: runId
        },
        couponCode: hasCoupon ? code : ""
      }
      const actions = {
        setSubmitting: helper.sandbox.stub(),
        setErrors:     helper.sandbox.stub()
      }
      await inner.find("CheckoutForm").prop("onSubmit")(values, actions)
      sinon.assert.calledWith(actions.setErrors, errors)
      sinon.assert.calledWith(actions.setSubmitting, false)
      sinon.assert.notCalled(submitStub)
      sinon.assert.calledWith(
        helper.handleRequestStub,
        "/api/basket/",
        "PATCH",
        {
          body: {
            items: [
              { product_id: basket.items[0].product_id, run_ids: [runId] }
            ],
            coupons:       hasCoupon ? [{ code: code }] : [],
            data_consents: []
          },
          credentials: undefined,
          headers:     {
            "X-CSRFTOKEN": null
          }
        }
      )
      sinon.assert.calledWith(helper.handleRequestStub, "/api/checkout/")
    })
  })

  it("displays no items if there are none in the basket", async () => {
    basket.items = []
    const { inner } = await renderPage()
    assert.equal(inner.text(), "No item in basket")
  })

  describe("calcSelectedRunIds", () => {
    it("calculates selected run ids from a basket item", () => {
      const item = basket.items[0]
      item.type = PRODUCT_TYPE_PROGRAM
      const expected = {}
      for (const runId of item.run_ids) {
        for (const course of item.courses) {
          for (const run of course.courseruns) {
            if (run.id === runId) {
              expected[course.id] = run.id
            }
          }
        }
      }
      assert.deepEqual(calcSelectedRunIds(item), expected)
    })
  })

  //
  ;["basketMutation", "couponsMutation", "checkoutMutation"].forEach(key => {
    it(`notifies CheckoutForm that a request is ongoing for ${key}`, async () => {
      const { inner } = await renderPage({
        queries: {
          [key]: {
            isPending: true
          }
        }
      })
      assert.isTrue(inner.find("CheckoutForm").prop("requestPending"))
    })
  })
})
