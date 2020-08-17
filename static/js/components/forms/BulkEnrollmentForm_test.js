// @flow
import React from "react"
import sinon from "sinon"
import { assert } from "chai"
import { mount } from "enzyme"

import { BulkEnrollmentForm } from "./BulkEnrollmentForm"
import {
  makeBulkCouponPayment,
  makeCourseRunProduct,
  makeCourseRunOrProgram
} from "../../factories/ecommerce"
import { findFormikFieldByName } from "../../lib/test_utils"
import { PRODUCT_TYPE_PROGRAM, PRODUCT_TYPE_COURSERUN } from "../../constants"

describe("BulkEnrollment", () => {
  let sandbox, submitRequestStub, bulkCouponPayments, productMap

  const defaultSubmitResponse = {
    body: {
      emails: ["a@b.com"]
    },
    status: 200
  }

  const createTestData = () => {
    const firstPayment = makeBulkCouponPayment(),
      secondPayment = makeBulkCouponPayment(),
      firstProduct = makeCourseRunProduct(),
      secondProduct = makeCourseRunProduct(),
      thirdProduct = makeCourseRunProduct(),
      fourthProduct = makeCourseRunProduct(),
      fifthProduct = makeCourseRunProduct(),
      sixthProduct = makeCourseRunProduct(),
      firstItem = makeCourseRunOrProgram(),
      secondItem = makeCourseRunOrProgram(),
      thirdItem = makeCourseRunOrProgram(PRODUCT_TYPE_COURSERUN, "b"),
      fourthItem = makeCourseRunOrProgram(PRODUCT_TYPE_COURSERUN, "b"),
      fifthItem = makeCourseRunOrProgram(PRODUCT_TYPE_COURSERUN, "a"),
      sixthItem = makeCourseRunOrProgram(PRODUCT_TYPE_PROGRAM)

    firstProduct.product_type = PRODUCT_TYPE_COURSERUN
    secondProduct.product_type = PRODUCT_TYPE_COURSERUN
    thirdProduct.product_type = PRODUCT_TYPE_COURSERUN
    fourthProduct.product_type = PRODUCT_TYPE_COURSERUN
    fifthProduct.product_type = PRODUCT_TYPE_COURSERUN
    sixthProduct.product_type = PRODUCT_TYPE_PROGRAM

    firstPayment.products = [firstProduct, secondProduct]
    secondPayment.products = [firstProduct]

    return {
      bulkCouponPayments: [firstPayment, secondPayment],
      products:           {
        [PRODUCT_TYPE_COURSERUN]: {
          [firstProduct.id.toString()]:  firstItem,
          [secondProduct.id.toString()]: secondItem,
          [thirdProduct.id.toString()]:  thirdItem,
          [fourthProduct.id.toString()]: fourthItem,
          [fifthProduct.id.toString()]:  fifthItem
        },
        [PRODUCT_TYPE_PROGRAM]: {
          [sixthProduct.id.toString()]: sixthItem
        }
      }
    }
  }

  const renderForm = (props = {}) =>
    mount(
      <BulkEnrollmentForm
        bulkCouponPayments={bulkCouponPayments}
        productMap={productMap}
        submitRequest={submitRequestStub}
        {...props}
      />
    )

  beforeEach(() => {
    sandbox = sinon.createSandbox()
    submitRequestStub = sandbox.stub().returns(defaultSubmitResponse)
    const testData = createTestData()
    bulkCouponPayments = testData.bulkCouponPayments
    productMap = testData.products
  })

  it("submits a request to send bulk enrollment emails", async () => {
    const dummyPayload = { dummy: "payload" }
    const setSubmitting = sandbox.stub(),
      resetForm = sandbox.stub(),
      setErrors = sandbox.stub()

    const wrapper = renderForm()
    const formProps = wrapper.find("Formik").props()
    await formProps.onSubmit(dummyPayload, {
      setSubmitting,
      resetForm,
      setErrors
    })
    sinon.assert.calledWith(submitRequestStub, dummyPayload)
    sinon.assert.calledWith(setSubmitting, false)
    sinon.assert.calledOnce(resetForm)
  })

  it("renders the form", () => {
    const wrapper = renderForm()
    const form = wrapper.find("Formik")
    assert.isTrue(form.find("input[name='users_file']").exists())
    assert.isTrue(findFormikFieldByName(form, "product_id").exists())
    assert.isTrue(findFormikFieldByName(form, "coupon_payment_id").exists())
    assert.isTrue(form.find("button[type='submit']").exists())
  })

  it("sorts products by readable_id", () => {
    const wrapper = renderForm()
    const form = wrapper.find("Formik")
    const options = form.find("select[name='product_id']").props().children
    const initialProductType = PRODUCT_TYPE_COURSERUN
    const sortedProductIds = Object.keys(productMap[initialProductType]).sort(
      (key1, key2) => {
        const sortKey = "courseware_id"
        if (
          productMap[initialProductType][key1][sortKey] <
          productMap[initialProductType][key2][sortKey]
        ) {
          return -1
        } else if (
          productMap[initialProductType][key1][sortKey] >
          productMap[initialProductType][key2][sortKey]
        ) {
          return 1
        }
        return 0
      }
    )
    assert.isTrue(sortedProductIds[0] === options[0].props.value)
    assert.isTrue(sortedProductIds[1] === options[1].props.value)
  })

  it("change product and product type", () => {
    const wrapper = renderForm()
    const form = wrapper.find("Formik")
    const options = form.find("select[name='product_id']").props().children

    // change product
    wrapper
      .find("select[name='product_id']")
      .simulate("change", { target: { value: options[1].props.value } })
    assert.isTrue(
      parseInt(wrapper.find("select[name='product_id']").props().value) ===
        parseInt(options[1].props.value)
    )

    wrapper
      .find("input[id='program']")
      .simulate("change", { currenTarget: { checked: true } })
    const productType = wrapper.find("input[id='program']")
    assert.isTrue(productType.props().checked)
  })
})
