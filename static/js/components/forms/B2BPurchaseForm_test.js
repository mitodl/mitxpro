// @flow
import React from "react"
import { mount, shallow } from "enzyme"
import sinon from "sinon"
import { assert } from "chai"

import { Field, Formik } from "formik"

import B2BPurchaseForm, { validate } from "./B2BPurchaseForm"
import ProductSelector from "../input/ProductSelector"
import configureStoreMain from "../../store/configureStore"

import {
  makeB2BCouponStatus,
  makeCourseRunProduct
} from "../../factories/ecommerce"
import { Provider } from "react-redux"

describe("B2BPurchaseForm", () => {
  let sandbox,
    onSubmitStub,
    products,
    fetchCouponStatusStub,
    clearCouponStatusStub,
    couponStatus,
    store

  beforeEach(() => {
    sandbox = sinon.createSandbox()
    store = configureStoreMain({})
    onSubmitStub = sandbox.stub()
    fetchCouponStatusStub = sandbox.stub()
    clearCouponStatusStub = sandbox.stub()
    products = [
      makeCourseRunProduct(),
      makeCourseRunProduct(),
      makeCourseRunProduct()
    ]
    couponStatus = makeB2BCouponStatus()
  })

  afterEach(() => {
    sandbox.restore()
  })

  const _render = (enzymeFunc, props = {}) =>
    /* Wrapping in <Provider /> now because ProductSelector needs access to the store */
    enzymeFunc(
      <Provider store={store}>
        <B2BPurchaseForm
          products={products}
          onSubmit={onSubmitStub}
          requestPending={false}
          fetchCouponStatus={fetchCouponStatusStub}
          contractNumber={null}
          clearCouponStatus={clearCouponStatusStub}
          couponStatus={couponStatus}
          productId="test+Aug_2016"
          discountCode="1234567890"
          seats="1"
          {...props}
        />
      </Provider>
    )

  const shallowRender = props => _render(shallow, props)
  const mountRender = props => _render(mount, props).first()

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
          product:   { productId: null, programId: null }
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
          product:   { productId: null, programId: null }
        }).num_seats,
        "Number of Seats is required"
      )
    })

    it("passes validation", () => {
      assert.deepEqual(
        validate({
          num_seats: "3",
          email:     "a@email.address",
          product:   { productId: "4", programRunId: null }
        }),
        {}
      )
    })
  })
})
