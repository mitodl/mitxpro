// @flow
import React from "react"
import { mount, shallow } from "enzyme"
import sinon from "sinon"
import { assert } from "chai"
import Decimal from "decimal.js-light"

import { Field, Formik } from "formik"

import B2BPurchaseForm, { validate } from "./B2BPurchaseForm"
import { makeProduct } from "../../factories/ecommerce"
import ProductSelector from "../input/ProductSelector"

describe("B2BPurchaseForm", () => {
  let sandbox, onSubmitStub, products

  beforeEach(() => {
    sandbox = sinon.createSandbox()

    onSubmitStub = sandbox.stub()
    products = [makeProduct(), makeProduct(), makeProduct()]
  })

  afterEach(() => {
    sandbox.restore()
  })

  const render = (props = {}) =>
    mount(
      <B2BPurchaseForm
        products={products}
        onSubmit={onSubmitStub}
        requestPending={false}
        {...props}
      />
    )

  it("renders a form", () => {
    const wrapper = render()

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
      const wrapper = render({ requestPending })
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
    const wrapper = shallow(
      <B2BPurchaseForm
        products={products}
        onSubmit={onSubmitStub}
        requestPending={false}
      />
    )
    const actions = {}
    const innerWrapper = shallow(
      shallow(wrapper.prop("render")({ values })).prop("children")(
        values,
        actions
      )
    )

    const numSeats = parseInt(values.num_seats)
    assert.deepEqual(innerWrapper.find("B2BPurchaseSummary").props(), {
      numSeats,
      totalPrice: new Decimal(selectedProduct.latest_version.price) * numSeats,
      itemPrice:  new Decimal(selectedProduct.latest_version.price)
    })
  })

  describe("validation", () => {
    it("has the validate function in the props", () => {
      const wrapper = render()
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
          num_seats: "Number of seats is required",
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
        "Number of seats is required"
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
})
