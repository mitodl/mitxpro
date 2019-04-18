// @flow
import React from "react"
import sinon from "sinon"
import { assert } from "chai"
import { mount } from "enzyme"
import wait from "waait"

import { CouponForm } from "./CouponForm"
import {
  findFormikFieldByName,
  findFormikErrorByName
} from "../../lib/test_utils"
import { makeCompany, makeProduct } from "../../factories/ecommerce"

describe("CouponForm", () => {
  let sandbox,
    onSubmitStub,
    selectProductsStub,
    toggleProductStub,
    toggleFormStub

  const renderForm = (isPromo: boolean = false) =>
    mount(
      <CouponForm
        onSubmit={onSubmitStub}
        selectProducts={selectProductsStub}
        toggleForm={toggleFormStub}
        toggleProduct={toggleProductStub}
        selectedProducts={[]}
        productType="courserun"
        isPromo={isPromo}
        products={[makeProduct(), makeProduct()]}
        companies={[makeCompany(), makeCompany()]}
      />
    )

  beforeEach(() => {
    sandbox = sinon.createSandbox()
    onSubmitStub = sandbox.stub()
    selectProductsStub = sandbox.stub()
    toggleProductStub = sandbox.stub()
    toggleFormStub = sandbox.stub()
  })

  it("passes onSubmit to Formik", () => {
    const wrapper = renderForm()
    assert.equal(wrapper.find("Formik").props().onSubmit, onSubmitStub)
  })

  it("renders the form", () => {
    const wrapper = renderForm()
    const form = wrapper.find("Formik")
    assert.ok(wrapper.find(".picky").exists())
    assert.ok(wrapper.find("DayPickerInput").at(1).exists)
    assert.ok(findFormikFieldByName(form, "product_type").exists())
    assert.ok(findFormikFieldByName(form, "coupon_type").exists())
    assert.ok(form.find("button[type='submit']").exists())
  })

  //
  ;[
    ["name", "", "Coupon name is required"],
    ["name", "Valid_name", null],
    ["name", "Invalid name", "Only letters, numbers, and underscores allowed"],
    ["amount", "", "Percentage discount is required"],
    ["amount", "0.5", "Must be at least 1"],
    ["amount", "-1", "Must be at least 1"],
    ["amount", "200", "Must be at most 100"],
    ["amount", "1", null],
    ["amount", "100", null]
  ].forEach(([name, value, errorMessage]) => {
    it(`validates the field name=${name}, value=${JSON.stringify(
      value
    )} and expects error=${JSON.stringify(errorMessage)}`, async () => {
      const wrapper = renderForm()

      const input = wrapper.find(`input[name="${name}"]`)
      input.simulate("change", { persist: () => {}, target: { name, value } })
      input.simulate("blur")
      await wait()
      wrapper.update()
      assert.deepEqual(
        findFormikErrorByName(wrapper, name).text(),
        errorMessage
      )
    })
  })

  //
  ;[
    ["expiration_date", 1, "", "Valid expiration date required"],
    ["activation_date", 0, "", "Valid activation date required"],
    ["expiration_date", 1, "bad_date", "Valid expiration date required"],
    ["activation_date", 0, "bad_date", "Valid activation date required"],
    ["expiration_date", 1, "2019-04-11T19:54:33.391Z", null],
    ["activation_date", 0, "2020-04-11T19:54:33.391Z", null]
  ].forEach(([name, idx, value, errorMessage]) => {
    it(`validates the field name=${name}, value=${JSON.stringify(
      value
    )} and expects error=${JSON.stringify(errorMessage)}`, async () => {
      const wrapper = renderForm()

      const input = wrapper
        .find("DayPickerInput")
        .at(idx)
        .find("input")
      input.simulate("click")
      input.simulate("change", { persist: () => {}, target: { name, value } })
      input.simulate("blur")
      await wait()
      wrapper.update()
      assert.deepEqual(
        findFormikErrorByName(wrapper, name).text(),
        errorMessage
      )
    })
  })

  //
  ;[
    [[], "1 or more products must be selected"],
    [[makeProduct()], null]
  ].forEach(([value, errorMessage]) => {
    it(`validates the field name=products, value="${JSON.stringify(
      value
    )}" and expects error=${JSON.stringify(
      errorMessage
    )} for coupons`, async () => {
      const wrapper = renderForm()
      const formik = wrapper.find("Formik").instance()
      formik.setFieldValue("products", value)
      formik.setFieldTouched("products")
      await wait()
      wrapper.update()
      assert.deepEqual(
        findFormikErrorByName(wrapper, "products").text(),
        errorMessage
      )
    })
  })

  it(`calls toggleProduct() when the product type is changed`, async () => {
    const wrapper = renderForm()
    const courseProductChoice = findFormikFieldByName(
      wrapper,
      "product_type"
    ).at(1)
    courseProductChoice.simulate("click")
    sinon.assert.calledWith(toggleProductStub)
  })

  it(`calls toggleForm() when the coupon type is changed`, async () => {
    const wrapper = renderForm()
    const couponTypeChoice = findFormikFieldByName(wrapper, "coupon_type").at(1)
    couponTypeChoice.simulate("click")
    sinon.assert.calledWith(toggleFormStub)
  })

  //
  ;[
    ["payment_type", "select", "", "Payment type is required"],
    ["payment_type", "select", "credit_card", null],
    ["payment_transaction", "input", "", "Payment transaction is required"],
    ["payment_transaction", "input", "number", null],
    ["num_coupon_codes", "input", "", "Number required"],
    ["num_coupon_codes", "input", "0", "Must be at least 1"],
    ["num_coupon_codes", "input", "2", null]
  ].forEach(([name, tag, value, errorMessage]) => {
    it(`validates the field name=${name}, value=${JSON.stringify(
      value
    )} and expects error=${JSON.stringify(
      errorMessage
    )} for single-use coupons`, async () => {
      const wrapper = renderForm()
      wrapper.find(`input[value="single-use"]`).simulate("click")
      const input = wrapper.find(`${tag}[name="${name}"]`)
      input.simulate("change", { persist: () => {}, target: { name, value } })
      input.simulate("blur")
      await wait()
      wrapper.update()
      assert.deepEqual(
        findFormikErrorByName(wrapper, name).text(),
        errorMessage
      )
    })
  })

  //
  ;[
    ["", "Coupon code is required"],
    ["VALIDCODE", null],
    ["INVALID CODE", "Only letters, numbers, and underscores allowed"]
  ].forEach(([value, errorMessage]) => {
    it(`validates the field name=coupon_code, value="${value}" and expects error=${JSON.stringify(
      errorMessage
    )} for promo coupons`, async () => {
      const wrapper = renderForm(true)
      const input = wrapper.find(`input[name="coupon_code"]`)
      input.simulate("change", {
        persist: () => {},
        target:  { name: "coupon_code", value: value }
      })
      input.simulate("blur")
      await wait()
      wrapper.update()
      assert.deepEqual(
        findFormikErrorByName(wrapper, "coupon_code").text(),
        errorMessage
      )
    })
  })
})
