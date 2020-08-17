// @flow
import { assert } from "chai"
import * as sinon from "sinon"

import CreateCouponPage, {
  CreateCouponPage as InnerCreateCouponPage
} from "./CreateCouponPage"
import {
  makeCompany,
  makeCouponPaymentVersion,
  makeCourseRunProduct,
  makeProgramProduct
} from "../../../factories/ecommerce"
import { COUPON_TYPE_PROMO, COUPON_TYPE_SINGLE_USE } from "../../../constants"
import IntegrationTestHelper from "../../../util/integration_test_helper"

describe("CreateCouponPage", () => {
  let helper,
    products,
    companies,
    renderCreateCouponPage,
    setSubmittingStub,
    setErrorsStub

  beforeEach(() => {
    helper = new IntegrationTestHelper()
    products = [makeCourseRunProduct(), makeProgramProduct()]
    companies = [makeCompany(), makeCompany()]
    setSubmittingStub = helper.sandbox.stub()
    setErrorsStub = helper.sandbox.stub()
    renderCreateCouponPage = helper.configureHOCRenderer(
      CreateCouponPage,
      InnerCreateCouponPage,
      {
        entities: {
          products,
          companies
        }
      },
      {}
    )
  })

  afterEach(() => {
    helper.cleanup()
  })

  it("displays a coupon form on the page", async () => {
    const { inner } = await renderCreateCouponPage()
    assert.isTrue(inner.find("CouponForm").exists())
  })

  it("displays a promo coupon success message on the page", async () => {
    const newCoupon = makeCouponPaymentVersion(true)
    const { inner } = await renderCreateCouponPage({
      entities: {
        coupons: { [newCoupon.id]: newCoupon }
      }
    })
    await inner.instance().setState({ couponId: newCoupon.id })
    assert.equal(
      inner.find(".coupon-success-div").text(),
      `Coupon "${newCoupon.payment.name}" successfully created.`
    )
  })

  it("displays a single-use coupon success message/link on the page", async () => {
    const newCoupon = makeCouponPaymentVersion(false)
    const { inner } = await renderCreateCouponPage({
      entities: {
        coupons: { [newCoupon.id]: newCoupon }
      }
    })
    await inner.instance().setState({ couponId: newCoupon.id })
    assert.equal(
      inner
        .find(".coupon-success-div")
        .find("a")
        .prop("href"),
      `/couponcodes/${newCoupon.id}`
    )
    assert.equal(
      inner.find(".coupon-success-div").text(),
      `Download coupon codes for "${newCoupon.payment.name}"`
    )
  })

  it("sets state.couponId to new coupon id if submission is successful", async () => {
    const testCouponData = {
      coupon_type:     COUPON_TYPE_PROMO,
      products:        [products[0]],
      max_redemptions: 100,
      coupon_code:     "HALFOFF",
      amount:          50
    }
    const newCoupon = makeCouponPaymentVersion()
    helper.handleRequestStub.returns({
      body:        newCoupon,
      transformed: { coupons: { [newCoupon.id]: newCoupon } }
    })
    const { inner } = await renderCreateCouponPage(
      {},
      {
        createCoupon: helper.handleRequestStub
      }
    )

    await inner.instance().onSubmit(testCouponData, {
      setSubmitting: setSubmittingStub,
      setErrors:     setErrorsStub
    })
    sinon.assert.calledWith(setSubmittingStub, false)
    sinon.assert.notCalled(setErrorsStub)
    sinon.assert.calledWith(helper.handleRequestStub, "/api/coupons/", "POST", {
      body:    testCouponData,
      headers: {
        "X-CSRFTOKEN": null
      },
      credentials: undefined
    })
    assert.equal(inner.state().couponId, newCoupon.id)
  })

  it("sets max_redemptions to 1 if coupon type is single-use", async () => {
    const testCouponData = {
      coupon_type:      COUPON_TYPE_SINGLE_USE,
      products:         [products[0]],
      num_coupon_codes: 100,
      amount:           50
    }
    const { inner } = await renderCreateCouponPage(
      {},
      {
        createCoupon: helper.handleRequestStub
      }
    )
    await inner.instance().onSubmit(testCouponData, {
      setSubmitting: setSubmittingStub,
      setErrors:     setErrorsStub
    })
    sinon.assert.calledWith(helper.handleRequestStub, "/api/coupons/", "POST", {
      body: {
        max_redemptions: 1,
        ...testCouponData
      },
      headers: {
        "X-CSRFTOKEN": null
      },
      credentials: undefined
    })
  })

  it("sets errors if submission is unsuccessful", async () => {
    const testCouponData = { products: [] }
    helper.handleRequestStub.returns({
      body: {
        errors: [
          { products: "Must select a product" },
          { name: "Must be unique" }
        ]
      }
    })
    const { inner } = await renderCreateCouponPage()
    await inner.instance().onSubmit(testCouponData, {
      setSubmitting: setSubmittingStub,
      setErrors:     setErrorsStub
    })
    sinon.assert.calledWith(setSubmittingStub, false)
    sinon.assert.calledWith(setErrorsStub, {
      products: "Must select a product",
      name:     "Must be unique"
    })
    assert.isTrue(inner.instance().state.couponId === null)
  })

  it("clearSuccess() changes state.couponId", async () => {
    const { inner } = await renderCreateCouponPage()
    inner.instance().setState({ couponId: 99 })
    assert.equal(inner.state().couponId, 99)
    inner.instance().clearSuccess()
    assert.equal(inner.state().couponId, null)
  })
})
