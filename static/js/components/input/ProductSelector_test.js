// @flow
import React from "react"
import { clone } from "ramda"
import sinon from "sinon"
import { shallow } from "enzyme"
import { assert } from "chai"
import casual from "casual-browserify"
// $FlowFixMe: Flow trips up with this library
import Select from "react-select"

import ProductSelector from "./ProductSelector"

import { makeProduct } from "../../factories/ecommerce"
import { PRODUCT_TYPE_COURSERUN, PRODUCT_TYPE_PROGRAM } from "../../constants"
import { findRunInProduct, formatRunTitle } from "../../lib/ecommerce"

describe("ProductSelector", () => {
  let sandbox,
    products,
    fieldValue,
    name,
    onChangeStub,
    runProduct2Course1,
    runProduct1Course1,
    runProduct2,
    programProduct

  beforeEach(() => {
    sandbox = sinon.createSandbox()
    name = casual.text
    onChangeStub = sandbox.stub()
    runProduct1Course1 = makeProduct(PRODUCT_TYPE_COURSERUN)
    runProduct2Course1 = makeProduct(PRODUCT_TYPE_COURSERUN)
    runProduct2Course1.latest_version.courses = clone(
      runProduct1Course1.latest_version.courses
    )
    runProduct1Course1.latest_version.object_id =
      runProduct1Course1.latest_version.courses[0].courseruns[0].id
    runProduct2Course1.latest_version.object_id =
      runProduct2Course1.latest_version.courses[0].courseruns[1].id
    runProduct2 = makeProduct(PRODUCT_TYPE_COURSERUN)
    programProduct = makeProduct(PRODUCT_TYPE_PROGRAM)
    products = [
      runProduct2,
      programProduct,
      runProduct1Course1,
      runProduct2Course1
    ]
    fieldValue = null
  })

  afterEach(() => {
    sandbox.restore()
  })

  const render = () =>
    shallow(
      <ProductSelector
        products={products}
        field={{
          onChange: onChangeStub,
          onBlur:   sandbox.stub(),
          name,
          value:    fieldValue
        }}
        form={{
          touched: false,
          errors:  {},
          values:  {}
        }}
      />
    )

  ;[PRODUCT_TYPE_COURSERUN, PRODUCT_TYPE_PROGRAM].forEach(productType => {
    describe(`for productType ${productType}`, () => {
      it("renders a Select widget", () => {
        const wrapper = render()
        wrapper.setState({ productType })
        const select = wrapper.find(Select).at(0)
        assert.deepEqual(select.prop("options"), [
          {
            label: "Course",
            value: PRODUCT_TYPE_COURSERUN
          },
          {
            label: "Program",
            value: PRODUCT_TYPE_PROGRAM
          }
        ])
      })
      ;[true, false].forEach(shouldChange => {
        it(`${
          shouldChange ? "changes" : "doesn't changes"
        } productType`, () => {
          const wrapper = render()
          const opposite =
            productType === PRODUCT_TYPE_PROGRAM
              ? PRODUCT_TYPE_COURSERUN
              : PRODUCT_TYPE_PROGRAM
          wrapper.setState({
            productType: shouldChange ? opposite : productType
          })
          const selectWrapper = wrapper.find(Select).at(0)
          selectWrapper.prop("onChange")({ value: productType })
          assert.equal(wrapper.state().productType, productType)
          if (shouldChange) {
            sinon.assert.calledWith(onChangeStub, {
              target: { name: name, value: "" }
            })
          } else {
            sinon.assert.notCalled(onChangeStub)
          }
        })
      })
    })
  })

  it("renders a list of programs", () => {
    const wrapper = render()
    wrapper.setState({
      productType: PRODUCT_TYPE_PROGRAM
    })
    const selectWrapper = wrapper.find(Select).at(1)
    assert.deepEqual(selectWrapper.prop("options"), [
      {
        label: programProduct.title,
        value: programProduct.id
      }
    ])
  })

  it("renders only one course per course run", () => {
    const wrapper = render()
    wrapper.setState({
      productType: PRODUCT_TYPE_COURSERUN
    })
    const selectWrapper = wrapper.find(Select).at(1)
    assert.deepEqual(selectWrapper.prop("options"), [
      {
        label: findRunInProduct(runProduct2)[1].title,
        value: runProduct2.id
      },
      {
        label: findRunInProduct(runProduct1Course1)[1].title,
        value: runProduct1Course1.id
      }
    ])
  })

  it("changes the selected program", () => {
    const wrapper = render()
    wrapper.setState({
      productType: PRODUCT_TYPE_PROGRAM
    })
    const selectWrapper = wrapper.find(Select).at(1)
    selectWrapper.prop("onChange")({ value: "new option" })
    sinon.assert.calledWith(onChangeStub, {
      target: { name, value: "new option" }
    })
  })

  it("doesn't change the selected program if it's the same as before", () => {
    fieldValue = runProduct2Course1.id
    const wrapper = render()
    wrapper.setState({
      productType: PRODUCT_TYPE_PROGRAM
    })
    const selectWrapper = wrapper.find(Select).at(1)
    selectWrapper.prop("onChange")({ value: runProduct2Course1.id })
    sinon.assert.notCalled(onChangeStub)
  })

  it("changes the selected course", () => {
    const wrapper = render()
    wrapper.setState({
      productType: PRODUCT_TYPE_COURSERUN
    })
    const selectWrapper = wrapper.find(Select).at(1)
    selectWrapper.prop("onChange")({ value: runProduct2.id })
    assert.deepEqual(wrapper.state().selected, [
      runProduct2,
      ...findRunInProduct(runProduct2)
    ])
    sinon.assert.calledWith(onChangeStub, { target: { name, value: null } })
  })

  it("doesn't change the selected course because it was already selected", () => {
    const wrapper = render()
    wrapper.setState({
      productType: PRODUCT_TYPE_COURSERUN,
      selected:    [runProduct2, ...findRunInProduct(runProduct2)]
    })
    const selectWrapper = wrapper.find(Select).at(1)
    selectWrapper.prop("onChange")({ value: runProduct2.id })
    assert.deepEqual(wrapper.state().selected, [
      runProduct2,
      ...findRunInProduct(runProduct2)
    ])
    sinon.assert.notCalled(onChangeStub)
  })

  it("doesn't render a list of course run dates if the program type is selected", () => {
    const wrapper = render()
    wrapper.setState({
      productType: PRODUCT_TYPE_PROGRAM
    })
    assert.isFalse(
      wrapper
        .find(Select)
        .at(2)
        .exists()
    )
  })

  it("renders a list of course run dates", () => {
    const wrapper = render()
    wrapper.setState({
      productType: PRODUCT_TYPE_COURSERUN,
      selected:    [runProduct2Course1, ...findRunInProduct(runProduct2Course1)]
    })

    const selectWrapper = wrapper.find(Select).at(2)
    assert.deepEqual(selectWrapper.prop("options"), [
      {
        label: formatRunTitle(findRunInProduct(runProduct1Course1)[0]),
        value: runProduct1Course1.id
      },
      {
        label: formatRunTitle(findRunInProduct(runProduct2Course1)[0]),
        value: runProduct2Course1.id
      }
    ])
  })

  it("changes the selected course run date", () => {
    const wrapper = render()
    wrapper.setState({
      productType:           PRODUCT_TYPE_COURSERUN,
      selectedCourseProduct: runProduct2Course1
    })
    const selectWrapper = wrapper.find(Select).at(2)
    selectWrapper.prop("onChange")({ value: "new option" })
    sinon.assert.calledWith(onChangeStub, {
      target: { name, value: "new option" }
    })
  })
})
