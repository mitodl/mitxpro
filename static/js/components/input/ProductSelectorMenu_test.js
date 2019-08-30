// @flow
import React from "react"
import sinon from "sinon"
import { shallow } from "enzyme"
import { assert } from "chai"
import { sortBy } from "ramda"

import ProductSelectorMenu from "./ProductSelectorMenu"

import { makeProduct } from "../../factories/ecommerce"
import { PRODUCT_TYPE_COURSERUN, PRODUCT_TYPE_PROGRAM } from "../../constants"
import type { ProductDetail } from "../../flow/ecommerceTypes"

describe("ProductSelectorMenu", () => {
  let sandbox,
    products,
    productType,
    onChangeStub,
    name,
    selectedProductId,
    toggleDropdownStub

  beforeEach(() => {
    sandbox = sinon.createSandbox()

    products = [makeProduct(), makeProduct(), makeProduct()]
    productType = PRODUCT_TYPE_COURSERUN
    onChangeStub = sandbox.stub()
    name = "the product selector menu field name"
    selectedProductId = null
    toggleDropdownStub = sandbox.stub()
  })

  afterEach(() => {
    sandbox.restore()
  })

  const render = (props = {}) =>
    shallow(
      <ProductSelectorMenu
        products={products}
        productType={productType}
        onChange={onChangeStub}
        name={name}
        toggleDropdown={toggleDropdownStub}
        selectedProductId={selectedProductId}
        {...props}
      />
    )

  const sortKeyFunc = (product: ProductDetail) =>
    `${product.title}-${product.latest_version.created_on}`

  ;[PRODUCT_TYPE_COURSERUN, PRODUCT_TYPE_PROGRAM].forEach(_productType => {
    it(`renders a product selector menu with ${_productType} selected`, () => {
      productType = _productType

      const product = makeProduct(productType)
      products = [...products, product]
      selectedProductId = product.id
      const wrapper = render()
      assert.equal(
        wrapper.find(".header").text(),
        productType === PRODUCT_TYPE_PROGRAM ? "Programs" : "Courses"
      )

      const filteredProducts = sortBy(
        sortKeyFunc,
        products.filter(_product => _product.product_type === productType)
      )
      assert.equal(filteredProducts.length, wrapper.find(".menu-item").length)
      filteredProducts.forEach((product, i) => {
        const div = wrapper.find(".menu-item").at(i)
        if (product.id === selectedProductId) {
          assert.equal(div.prop("className"), "menu-item selected")
        } else {
          assert.equal(div.prop("className"), "menu-item ")
        }

        assert.equal(div.find("img").prop("alt"), `Image for ${product.title}`)
        assert.equal(
          div.find("img").prop("src"),
          product.latest_version.thumbnail_url
        )
        assert.isTrue(
          div
            .find(".menu-item-description")
            .text()
            .includes(product.title)
        )
        onChangeStub.resetHistory()
        div.prop("onClick")({ preventDefault: sandbox.stub() })
        sinon.assert.calledWith(onChangeStub, {
          target: {
            value: product.id,
            name:  name
          }
        })
      })
    })
  })
})
