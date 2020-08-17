// @flow
import sinon from "sinon"
import { assert } from "chai"

import IntegrationTestHelper from "../../../util/integration_test_helper"
import B2BPurchasePage, {
  B2BPurchasePage as InnerB2BPurchasePage
} from "./B2BPurchasePage"

import * as formFuncs from "../../../lib/form"
import {
  makeB2BCouponStatus,
  makeCourseRunProduct,
  makeProgramProduct
} from "../../../factories/ecommerce"

describe("B2BPurchasePage", () => {
  let helper, renderPage, products

  beforeEach(() => {
    helper = new IntegrationTestHelper()
    products = [
      makeCourseRunProduct(),
      makeCourseRunProduct(),
      makeProgramProduct("test+Aug_2016")
    ]
    renderPage = helper.configureHOCRenderer(
      B2BPurchasePage,
      InnerB2BPurchasePage,
      {
        entities: {
          products
        },
        queries: {
          products: {
            isPending: false
          }
        }
      },
      {
        location: {
          search: "product_id=test-course-v1:MITx+Digital+Learning+300+Aug_2016"
        }
      }
    )
  })

  afterEach(() => {
    helper.cleanup()
  })

  it("loads products on mount", async () => {
    await renderPage()
    helper.handleRequestStub.withArgs("/api/products/", "POST").returns({
      body:   undefined,
      status: 200
    })
  })

  it("displays loader", async () => {
    const { inner } = await renderPage()
    inner.setProps({ isLoading: true })
    assert.equal(
      inner.find(".page").text(),
      "One moment while we prepare bulk purchase page"
    )
  })

  it("renders a form", async () => {
    const { inner } = await renderPage()
    const props = inner.find("B2BPurchaseForm").props()
    assert.deepEqual(
      props.products,
      products.filter(product => product.visible_in_bulk_form === true)
    )
  })

  describe("submission", () => {
    let actions

    beforeEach(() => {
      actions = {
        setSubmitting: helper.sandbox.stub(),
        setErrors:     helper.sandbox.stub()
      }
    })
    ;[["xyz", "applies"], ["", "clears"]].forEach(([couponCode, desc]) => {
      it(`${desc} a coupon`, async () => {
        const couponStatus = couponCode ? makeB2BCouponStatus() : null
        const { inner } = await renderPage({
          entities: {
            b2b_coupon_status: couponStatus
          }
        })

        const url = "/api/b2b/checkout/"
        const payload = { pay: "load" }
        helper.handleRequestStub
          .withArgs("/api/b2b/checkout/", "POST")
          .returns({
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
        const selectedProduct = products[1]
        const values = {
          product:   { productId: selectedProduct.id, programRunId: null },
          num_seats: 5,
          email:     "email@example.com"
        }
        await inner.find("B2BPurchaseForm").prop("onSubmit")(values, actions)
        sinon.assert.calledWith(createFormStub, url, payload)
        sinon.assert.calledWith(submitStub)
        sinon.assert.calledWith(
          helper.handleRequestStub,
          "/api/b2b/checkout/",
          "POST",
          {
            body: {
              email:              values.email,
              product_version_id: selectedProduct.latest_version.id,
              num_seats:          values.num_seats,
              discount_code:      couponStatus ? couponStatus.code : null,
              contract_number:    null,
              run_id:             null
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

    it("submits the form but redirects to a location instead of submitting a form to CyberSource", async () => {
      const { inner } = await renderPage()

      const url = "/a/b/c/"
      const payload = { pay: "load" }
      helper.handleRequestStub.withArgs("/api/b2b/checkout/", "POST").returns({
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
      const selectedProduct = products[1]
      const values = {
        product:   { productId: "test+Aug_2016", programRunId: null },
        num_seats: 5,
        email:     "email@example.com"
      }
      await inner.find("B2BPurchaseForm").prop("onSubmit")(values, actions)

      sinon.assert.notCalled(actions.setErrors)
      sinon.assert.calledWith(actions.setSubmitting, false)
      assert.isTrue(window.location.toString().endsWith(url))
    })

    it("submits the form but receives an error", async () => {
      const { inner } = await renderPage()

      const errors = "some errors 😩"
      helper.handleRequestStub.withArgs("/api/b2b/checkout/", "POST").returns({
        body: {
          errors
        },
        status: 500
      })
      const selectedProduct = products[1]
      const values = {
        product:   { productId: selectedProduct.id, programRunId: null },
        num_seats: 5,
        email:     "email@example.com"
      }
      await inner.find("B2BPurchaseForm").prop("onSubmit")(values, actions)
      sinon.assert.calledWith(actions.setErrors, errors)
      sinon.assert.calledWith(actions.setSubmitting, false)
    })
  })

  it("fetches coupon status", async () => {
    const couponStatus = makeB2BCouponStatus()
    const { inner, store } = await renderPage({})
    helper.handleRequestStub
      .withArgs("/api/b2b/coupon_status/", "GET")
      .returns({
        body:   couponStatus,
        status: 200
      })
    const payload = { pay: "load" }
    await inner.find("B2BPurchaseForm").prop("fetchCouponStatus")(payload)
    assert.deepEqual(store.getState().entities.b2b_coupon_status, couponStatus)
    sinon.assert.calledWith(
      helper.handleRequestStub,
      "/api/b2b/coupon_status/",
      "GET",
      {
        body:        payload,
        headers:     undefined,
        credentials: undefined
      }
    )
  })

  it("clears coupon status", async () => {
    const couponStatus = makeB2BCouponStatus()
    const { inner, store } = await renderPage({
      entities: {
        b2b_coupon_status: couponStatus
      }
    })
    inner.find("B2BPurchaseForm").prop("clearCouponStatus")()
    assert.isNull(store.getState().entities.b2b_coupon_status)
  })

  it("sets requestPending when a request is in progress", async () => {
    const { inner } = await renderPage({
      queries: {
        products: {
          isPending: false
        },
        b2bCheckoutMutation: {
          isPending: true
        }
      }
    })
    assert.isTrue(inner.find("B2BPurchaseForm").prop("requestPending"))
  })
})
