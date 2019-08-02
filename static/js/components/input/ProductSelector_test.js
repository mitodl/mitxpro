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
  let sandbox, products, value, name, onChangeStub

  beforeEach(() => {
    sandbox = sinon.createSandbox()
    name = casual.text
    onChangeStub = sandbox.stub()
    products = [
      makeProduct(PRODUCT_TYPE_COURSERUN),
      makeProduct(PRODUCT_TYPE_PROGRAM),
      makeProduct(PRODUCT_TYPE_COURSERUN)
    ]
    value = {}
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
          value
        }}
        form={{
          touched: false,
          errors:  {},
          values:  {}
        }}
      />
    )

  ;["courserun", "program"].forEach(productType => {
    it(`renders a button with ${productType} selected`, () => {
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
        productType === "courserun" ? "selected" : ""
      )
      assert.equal(
        programWrapper.prop("className"),
        productType === "program" ? "selected" : ""
      )
    })

    it(`changes state to ${productType} on click`, () => {
      const wrapper = render()
      const [courseButton, programButton] = wrapper.find("button")
      const button = productType === "courserun" ? courseButton : programButton
      shallow(button).prop("onClick")({ preventDefault: sandbox.stub() })
      wrapper.update()
      assert.equal(wrapper.state().productType, productType)
    })

    it(`shows a list of products for ${productType}`, () => {
      const wrapper = render()
      wrapper.setState({ productType })
      const [pickOption, ...options] = wrapper.find("option")
      assert.equal(shallow(pickOption).text(), "Select a product")
      assert.equal(shallow(pickOption).prop("value"), "")
      const filteredProducts = products.filter(
        product => product.product_type === productType
      )
      assert.equal(options.length, filteredProducts.length)
      filteredProducts.forEach((product, i) => {
        const option = shallow(options[i])
        assert.equal(option.text(), product.title)
        assert.equal(option.prop("value"), product.id)
      })
    })

    it(`clears the selection when ${productType} is set but a different button is clicked`, () => {
      const wrapper = render()
      wrapper.setState({ productType })
      const [courseButton, programButton] = wrapper.find("button")
      const otherButton =
        productType === PRODUCT_TYPE_COURSERUN ? programButton : courseButton
      shallow(otherButton).prop("onClick")({ preventDefault: sandbox.stub() })
      sinon.assert.calledWith(onChangeStub, { target: { value: "", name } })
    })

    it(`does not clear the selection when ${productType} is set but a different button is clicked`, () => {
      const wrapper = render()
      wrapper.setState({ productType })
      const [courseButton, programButton] = wrapper.find("button")
      const sameButton =
        productType === PRODUCT_TYPE_COURSERUN ? courseButton : programButton
      shallow(sameButton).prop("onClick")({ preventDefault: sandbox.stub() })
      sinon.assert.notCalled(onChangeStub)
    })
  })

  it("uses the value for the selected product", () => {
    value.product = 98765
    const wrapper = render()
    assert.equal(wrapper.find("select").prop("value"), value.product)
    assert.equal(wrapper.find("select").prop("name"), name)
  })

  it("updates the selected option", () => {
    const wrapper = render()
    assert.equal(wrapper.find("select").prop("onChange"), onChangeStub)
  })
})
