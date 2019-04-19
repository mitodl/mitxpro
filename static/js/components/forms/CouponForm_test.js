// @flow
import React from "react"
import sinon from "sinon"
import moment from "moment"
import { assert } from "chai"
import { mount } from "enzyme"
import wait from "waait"

import { CouponForm } from "./CouponForm"
import { COUPON_TYPE_PROMO } from "../../constants"
import { makeCompany, makeProduct } from "../../factories/ecommerce"
import {
  findFormikFieldByName,
  findFormikErrorByName
} from "../../lib/test_utils"

describe("CouponForm", () => {
  let sandbox, onSubmitStub

  const renderForm = () =>
    mount(
      <CouponForm
        onSubmit={onSubmitStub}
        products={[makeProduct(), makeProduct()]}
        companies={[makeCompany(), makeCompany()]}
      />
    )

  beforeEach(() => {
    sandbox = sinon.createSandbox()
    onSubmitStub = sandbox.stub()
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
    ["discount", "", "Percentage discount is required"],
    ["discount", "0.5", "Must be at least 1"],
    ["discount", "-1", "Must be at least 1"],
    ["discount", "200", "Must be at most 100"],
    ["discount", "1", null],
    ["discount", "100", null],
    ["payment_transaction", "", "Payment transaction is required"],
    ["payment_transaction", "number", null],
    ["num_coupon_codes", "", "Number required"],
    ["num_coupon_codes", "0", "Must be at least 1"],
    ["num_coupon_codes", "2", null]
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
    [
      "expiration_date",
      1,
      moment().format("YYYY-MM-DD"),
      "Date cannot be less than activation date"
    ],
    ["activation_date", 0, moment().format("YYYY-MM-DD"), null],
    ["activation_date", 0, "2001-01-01T00:00:00Z", "Date cannot be in the past"]
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

  //
  ;[
    ["payment_type", "", "Payment type is required"],
    ["payment_type", "credit_card", null]
  ].forEach(([name, value, errorMessage]) => {
    it(`validates the field name=${name}, value=${JSON.stringify(
      value
    )} and expects error=${JSON.stringify(
      errorMessage
    )} for single-use coupons`, async () => {
      const wrapper = renderForm()
      wrapper.find(`input[value="single-use"]`).simulate("click")
      const input = wrapper.find(`select[name="${name}"]`)
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
    ["coupon_code", "", "Coupon code is required"],
    ["coupon_code", "VALIDCODE", null],
    [
      "coupon_code",
      "INVALID CODE",
      "Only letters, numbers, and underscores allowed"
    ],
    ["max_redemptions", "", "Number required"],
    ["max_redemptions", "-10", "Must be at least 1"],
    ["max_redemptions", "10000", null]
  ].forEach(([name, value, errorMessage]) => {
    it(`validates the field name=${name}, value="${value}" and expects error=${JSON.stringify(
      errorMessage
    )} for promo coupons`, async () => {
      const wrapper = renderForm()
      findFormikFieldByName(wrapper, "coupon_type")
        .at(1)
        .simulate("change", {
          persist: () => {},
          target:  { name: "coupon_type", value: COUPON_TYPE_PROMO }
        })
      await wait()
      wrapper.update()
      const input = findFormikFieldByName(wrapper, name)
      input.simulate("change", {
        persist: () => {},
        target:  { name, value }
      })
      input.simulate("blur")
      await wait()
      wrapper.update()
      assert.deepEqual(
        findFormikErrorByName(wrapper, name).text(),
        errorMessage
      )
    })
  })
})
