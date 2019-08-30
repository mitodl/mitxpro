// @flow
import React from "react"
import sinon from "sinon"
import { shallow } from "enzyme"
import { assert } from "chai"
import casual from "casual-browserify"

import ProductSelector from "./ProductSelector"

import { makeProduct } from "../../factories/ecommerce"
import { PRODUCT_TYPE_COURSERUN, PRODUCT_TYPE_PROGRAM } from "../../constants"

describe("ProductSelector", () => {
  let sandbox, products, fieldValue, name, onChangeStub

  beforeEach(() => {
    sandbox = sinon.createSandbox()
    name = casual.text
    onChangeStub = sandbox.stub()
    products = [
      makeProduct(PRODUCT_TYPE_COURSERUN),
      makeProduct(PRODUCT_TYPE_PROGRAM),
      makeProduct(PRODUCT_TYPE_COURSERUN)
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
      it("renders a button", () => {
        const wrapper = render()
        wrapper.setState({ productType })
        const [courseButton, programButton] = wrapper.find("button")
        const [courseWrapper, programWrapper] = [
          shallow(courseButton),
          shallow(programButton)
        ]
        assert.equal(courseWrapper.text(), "Course")
        assert.equal(programWrapper.text(), "Program")
        assert.equal(
          courseWrapper.prop("className"),
          productType === PRODUCT_TYPE_COURSERUN
            ? "selected select-product-type"
            : " select-product-type"
        )
        assert.equal(
          programWrapper.prop("className"),
          productType === PRODUCT_TYPE_PROGRAM
            ? "selected select-product-type"
            : " select-product-type"
        )
      })

      it("changes productType on click", () => {
        const wrapper = render()
        const [courseButton, programButton] = wrapper.find("button")
        const button =
          productType === "courserun" ? courseButton : programButton
        shallow(button).prop("onClick")({ preventDefault: sandbox.stub() })
        wrapper.update()
        assert.equal(wrapper.state().productType, productType)
      })

      it("clears the selection when the a different button is clicked", () => {
        const wrapper = render()
        wrapper.setState({ productType })
        const [courseButton, programButton] = wrapper.find("button")
        const otherButton =
          productType === PRODUCT_TYPE_COURSERUN ? programButton : courseButton
        shallow(otherButton).prop("onClick")({ preventDefault: sandbox.stub() })
        sinon.assert.calledWith(onChangeStub, { target: { value: "", name } })
      })

      it("does not clear the selection when a button already selected is clicked", () => {
        const wrapper = render()
        wrapper.setState({ productType })
        const [courseButton, programButton] = wrapper.find("button")
        const sameButton =
          productType === PRODUCT_TYPE_COURSERUN ? courseButton : programButton
        shallow(sameButton).prop("onClick")({ preventDefault: sandbox.stub() })
        sinon.assert.notCalled(onChangeStub)
      })

      it("renders a dropdown menu", () => {
        fieldValue = 98765
        const wrapper = render()
        wrapper.setState({ productType })
        const props = wrapper.find("ProductSelectorMenu").props()

        assert.equal(props.onChange, onChangeStub)
        assert.equal(props.productType, productType)
        assert.deepEqual(props.products, products)
        assert.equal(props.name, name)
        assert.equal(props.selectedProductId, fieldValue)
      })

      //
      ;[true, false].forEach(dropdownOpen => {
        it(`turns ${dropdownOpen ? "off" : "on"} dropdown visibility`, () => {
          const wrapper = render()
          wrapper.setState({ dropdownOpen })
          assert.equal(wrapper.find("Dropdown").prop("isOpen"), dropdownOpen)
          const toggleDropdown = wrapper
            .find("ProductSelectorMenu")
            .prop("toggleDropdown")
          toggleDropdown()
          assert.equal(wrapper.state().dropdownOpen, !dropdownOpen)
          assert.equal(wrapper.find("Dropdown").prop("isOpen"), !dropdownOpen)
        })
      })
    })
  })
})
