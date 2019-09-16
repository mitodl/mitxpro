// @flow
import React from "react"
import { mount, shallow } from "enzyme"
import sinon from "sinon"
import { assert } from "chai"
import Decimal from "decimal.js-light"

import { Field, Formik } from "formik"

import B2BPurchaseForm, { validate } from "./B2BPurchaseForm"
import ProductSelector from "../input/ProductSelector"

import { makeB2BCouponStatus, makeProduct } from "../../factories/ecommerce"

describe("B2BPurchaseForm", () => {
  let sandbox,
    onSubmitStub,
    products,
    fetchCouponStatusStub,
    clearCouponStatusStub,
    couponStatus

  beforeEach(() => {
    sandbox = sinon.createSandbox()

    onSubmitStub = sandbox.stub()
    fetchCouponStatusStub = sandbox.stub()
    clearCouponStatusStub = sandbox.stub()
    products = [makeProduct(), makeProduct(), makeProduct()]
    couponStatus = makeB2BCouponStatus()
  })

  afterEach(() => {
    sandbox.restore()
  })

  const _render = (enzymeFunc, props = {}) =>
    enzymeFunc(
      <B2BPurchaseForm
        products={products}
        onSubmit={onSubmitStub}
        requestPending={false}
        fetchCouponStatus={fetchCouponStatusStub}
        clearCouponStatus={clearCouponStatusStub}
        couponStatus={couponStatus}
        {...props}
      />
    )

  const shallowRender = props => _render(shallow, props)
  const mountRender = props => _render(mount, props)

  it("renders a form", () => {
    const wrapper = mountRender()

    const [productSelectorProps, numSeatsProps, emailProps] = wrapper
      .find(Field)
      .map(_field => _field.props())

    assert.equal(productSelectorProps.name, "product")
    assert.deepEqual(productSelectorProps.products, products)
    assert.equal(productSelectorProps.component, ProductSelector)
    assert.equal(numSeatsProps.name, "num_seats")
    assert.equal(emailProps.name, "email")
  })

  //
  ;[true, false].forEach(requestPending => {
    it(`disables the submit button if the request is ${
      requestPending ? "pending" : "not pending"
    }`, () => {
      const wrapper = mountRender({ requestPending })
      assert.equal(
        wrapper.find("button[type='submit']").prop("disabled"),
        requestPending
      )
    })
  })

  //
  it("renders the order summary with correct price and quantity info", () => {
    const selectedProduct = products[2]
    const values = {
      num_seats: "5",
      product:   String(selectedProduct.id)
    }
    const wrapper = shallowRender()
    const actions = {}
    const innerWrapper = shallow(
      shallow(wrapper.prop("render")({ values })).prop("children")(
        values,
        actions
      )
    )

    const numSeats = parseInt(values.num_seats)
    const itemPrice = new Decimal(selectedProduct.latest_version.price)
    const discount = itemPrice
      .times(numSeats)
      .times(new Decimal(couponStatus.discount_percent))
    assert.deepEqual(innerWrapper.find("B2BPurchaseSummary").props(), {
      numSeats,
      totalPrice:  itemPrice.times(numSeats).minus(discount),
      itemPrice:   itemPrice,
      discount:    discount,
      alreadyPaid: false
    })
  })

  describe("validation", () => {
    it("has the validate function in the props", () => {
      const wrapper = mountRender()
      assert.equal(wrapper.find(Formik).prop("validate"), validate)
    })

    it("requires all fields", () => {
      assert.deepEqual(
        validate({
          num_seats: "",
          email:     "",
          product:   ""
        }),
        {
          email:     "Email is required",
          num_seats: "Number of Seats is required",
          product:   "No product selected"
        }
      )
    })

    it("requires a positive number for the number of seats", () => {
      assert.equal(
        validate({
          num_seats: "-2",
          email:     "",
          product:   ""
        }).num_seats,
        "Number of Seats is required"
      )
    })

    it("passes validation", () => {
      assert.deepEqual(
        validate({
          num_seats: "3",
          email:     "a@email.address",
          product:   "4"
        }),
        {}
      )
    })
  })

  describe("coupon submission", () => {
    let setFieldErrorStub, productId, newCode, wrapper

    beforeEach(() => {
      setFieldErrorStub = sandbox.stub()
      productId = 123
      fetchCouponStatusStub.returns(Promise.resolve({ status: 200 }))
      newCode = "xyz"

      wrapper = mountRender()
    })

    const renderForm = values =>
      shallow(
        shallow(
          wrapper.find(Formik).prop("render")({
            values,
            setFieldError: setFieldErrorStub
          })
        ).prop("children")(values)
      )

    //
    ;[["  xyz  ", "applies"], ["", "clears"]].forEach(([couponCode, desc]) => {
      it(`${desc} the given coupon value`, async () => {
        const values = {
          coupon:  couponCode,
          product: productId
        }
        const innerWrapper = renderForm(values)

        await innerWrapper.find(".apply-button").prop("onClick")({
          preventDefault: sandbox.stub()
        })
        if (couponCode) {
          sinon.assert.calledWith(fetchCouponStatusStub, {
            product_id: productId,
            code:       couponCode.trim()
          })
        } else {
          sinon.assert.calledWith(clearCouponStatusStub)
        }

        sinon.assert.notCalled(setFieldErrorStub)
      })
    })

    it("errors when applying the coupon because no product is selected", async () => {
      const values = {
        coupon:  newCode,
        product: ""
      }
      const innerWrapper = renderForm(values)

      await innerWrapper.find(".apply-button").prop("onClick")({
        preventDefault: sandbox.stub()
      })
      sinon.assert.notCalled(fetchCouponStatusStub)
      sinon.assert.calledWith(
        setFieldErrorStub,
        "coupon",
        "No product selected"
      )
    })

    it("errors because the coupon is invalid", async () => {
      fetchCouponStatusStub.returns(Promise.resolve({ status: 500 }))
      const values = {
        coupon:  newCode,
        product: productId
      }
      const innerWrapper = renderForm(values)

      await innerWrapper.find(".apply-button").prop("onClick")({
        preventDefault: sandbox.stub()
      })
      sinon.assert.calledWith(fetchCouponStatusStub, {
        product_id: productId,
        code:       newCode
      })
      sinon.assert.calledWith(
        setFieldErrorStub,
        "coupon",
        "Invalid coupon code"
      )
    })
  })
})
