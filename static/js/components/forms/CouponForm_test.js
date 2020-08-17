// @flow
import React from "react"
import sinon from "sinon"
import moment from "moment"
import { assert } from "chai"
import { mount } from "enzyme"
import wait from "waait"

import { CouponForm } from "./CouponForm"
import {
  COUPON_TYPE_PROMO,
  PRODUCT_TYPE_COURSERUN,
  PRODUCT_TYPE_PROGRAM
} from "../../constants"
import {
  makeCompany,
  makeCourseRunProduct,
  makeProgramProduct
} from "../../factories/ecommerce"
import {
  findFormikFieldByName,
  findFormikErrorByName
} from "../../lib/test_utils"
import { formatPrettyDate } from "../../lib/util"

describe("CouponForm", () => {
  let sandbox, onSubmitStub
  const products = [makeCourseRunProduct(), makeProgramProduct()]

  const renderForm = () =>
    mount(
      <CouponForm
        onSubmit={onSubmitStub}
        products={products}
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
    assert.ok(findFormikFieldByName(form, "is_global").exists())
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
    ["activation_date", 0, "06/27/2019", null],
    [
      "expiration_date",
      1,
      moment()
        .add(1, "days")
        .format("MM/DD/YYYY"),
      null
    ],
    [
      "expiration_date",
      1,
      moment()
        .subtract(1, "days")
        .format("MM/DD/YYYY"),
      "Expiration date must be after today/activation date"
    ]
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
    ["activation_date", 0, "06/27/2019", "2019-06-27T00:00:00.000Z"],
    ["expiration_date", 1, "06/27/2519", "2519-06-27T23:59:59.999Z"]
  ].forEach(([name, idx, value, formattedDate]) => {
    it(`converts the field name=${name}, value=${JSON.stringify(
      value
    )} to date string ${JSON.stringify(formattedDate)}`, async () => {
      const wrapper = renderForm()
      const formik = wrapper.find("Formik").instance()
      const input = wrapper
        .find("DayPickerInput")
        .at(idx)
        .find("input")
      input.simulate("click")
      input.simulate("change", { persist: () => {}, target: { name, value } })
      input.simulate("blur")
      await wait()
      wrapper.update()
      assert.equal(formik.state.values[name].toISOString(), formattedDate)
    })
  })

  //
  ;[
    [[], "1 or more products must be selected"],
    [[makeCourseRunProduct()], null]
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
    [PRODUCT_TYPE_COURSERUN, [products[0]]],
    [PRODUCT_TYPE_PROGRAM, [products[1]]],
    ["", products]
  ].forEach(([productType, availableProduct]) => {
    it(`displays correct product checkboxes when productType radio button value="${productType}"`, async () => {
      const wrapper = renderForm()
      wrapper
        .find(`input[name='product_type'][value='${productType}']`)
        .simulate("click")
      await wait()
      wrapper.update()
      const picky = wrapper.find(".picky")
      const options = picky.find("input[type='checkbox']")
      assert.equal(options.at(1).exists(), productType === "")
      assert.ok(picky.text().includes(availableProduct[0].content_object.title))
      if (productType === "") {
        assert.ok(
          picky.text().includes(availableProduct[1].content_object.title)
        )
      }
    })
  })

  //
  it(`displays correct product labels`, async () => {
    const wrapper = renderForm()
    wrapper
      .find(`input[name='product_type']`)
      .findWhere(checkBox => checkBox.prop("value") === "")
      .simulate("click")
    await wait()
    wrapper.update()
    const picky = wrapper.find(".picky")
    assert.ok(
      picky
        .text()
        .includes(
          `${products[0].latest_version.readable_id} | ${
            products[0].content_object.title
          } | ${formatPrettyDate(
            moment(products[0].content_object.start_date)
          )}`
        )
    )
    assert.ok(
      picky
        .text()
        .includes(
          `${products[1].latest_version.readable_id} | ${
            products[1].content_object.title
          }`
        )
    )
  })

  //
  ;[
    ["payment_type", "", "Payment type is required"],
    ["payment_type", "staff", null]
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
