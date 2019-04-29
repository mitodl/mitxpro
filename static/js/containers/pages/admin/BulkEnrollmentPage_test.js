// @flow
import { assert } from "chai"
import * as sinon from "sinon"

import BulkEnrollmentPage, {
  BulkEnrollmentPage as InnerBulkEnrollmentPage
} from "./BulkEnrollmentPage"
import { makeBulkCouponPayment } from "../../../factories/ecommerce"
import IntegrationTestHelper from "../../../util/integration_test_helper"
import { objectToFormData } from "../../../lib/util"

describe("BulkEnrollmentPage", () => {
  let helper, bulkCouponPayments, renderPage

  beforeEach(() => {
    helper = new IntegrationTestHelper()
    bulkCouponPayments = [makeBulkCouponPayment(), makeBulkCouponPayment()]
    renderPage = helper.configureHOCRenderer(
      BulkEnrollmentPage,
      InnerBulkEnrollmentPage,
      {
        entities: { bulkCouponPayments }
      },
      {}
    )
  })

  afterEach(() => {
    helper.cleanup()
  })

  it("renders a form", async () => {
    const { inner } = await renderPage()
    assert.isTrue(inner.find("BulkEnrollmentForm").exists())
  })

  it("shows an error message if no valid product coupons were returned by the API", async () => {
    const { inner } = await renderPage(
      { entities: { bulkCouponPayments: [] } },
      {}
    )
    assert.isFalse(inner.find("BulkEnrollmentForm").exists())
    assert.isTrue(inner.find("div.error").exists())
  })

  it("handles a form submission", async () => {
    const couponPaymentId = 123,
      productId = 321,
      dummyFile = { dummy: "file" }

    helper.handleRequestStub.returns({
      body: {
        emails:            ["abc@example.com"],
        product_id:        productId,
        coupon_payment_id: couponPaymentId
      }
    })
    const { inner } = await renderPage()
    await inner.instance().submitRequest({
      users_file:        dummyFile,
      product_id:        productId,
      coupon_payment_id: couponPaymentId
    })
    // One request is made to load product coupons, then another one for the form submission
    sinon.assert.calledTwice(helper.handleRequestStub)
    sinon.assert.calledWith(
      helper.handleRequestStub,
      "/api/bulk_enroll/",
      "POST",
      {
        body: objectToFormData({
          users_file:        dummyFile,
          product_id:        productId,
          coupon_payment_id: couponPaymentId
        }),
        headers: {
          "X-CSRFTOKEN": null
        },
        credentials: undefined
      }
    )
  })
})
