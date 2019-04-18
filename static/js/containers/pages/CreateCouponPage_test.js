// @flow
import { assert } from "chai"
import * as sinon from "sinon"

import { CreateCouponPage } from "./CreateCouponPage"
import { configureShallowRenderer } from "../../lib/test_utils"
import {
  makeCouponPaymentVersion,
  makeProduct
} from "../../factories/ecommerce"

describe("CreateCouponPage", () => {
  let sandbox,
    products,
    renderCreateCouponPage,
    setSubmittingStub,
    setErrorsStub

  beforeEach(() => {
    sandbox = sinon.createSandbox()
    products = [
      makeProduct("courserun"),
      makeProduct("course"),
      makeProduct("program")
    ]
    setSubmittingStub = sandbox.stub()
    setErrorsStub = sandbox.stub()
    renderCreateCouponPage = configureShallowRenderer(CreateCouponPage, {
      products: products
    })
  })

  afterEach(() => {
    sandbox.restore()
  })

  it("displays a coupon form on the page", () => {
    const wrapper = renderCreateCouponPage()
    assert.isTrue(wrapper.find("CouponForm").exists())
  })

  it("displays a promo coupon success message on the page", async () => {
    const newCoupon = makeCouponPaymentVersion(true)
    const wrapper = renderCreateCouponPage({ newCoupon })
    await wrapper.instance().setState({ created: true })
    assert.equal(
      wrapper.find(".coupon-success-div").text(),
      `Coupon "${newCoupon.payment.name}" successfully created.`
    )
  })

  it("displays a single-use coupon success message/link on the page", async () => {
    const newCoupon = makeCouponPaymentVersion(false)
    const wrapper = renderCreateCouponPage({ newCoupon })
    await wrapper.instance().setState({ created: true })
    assert.equal(
      wrapper
        .find(".coupon-success-div")
        .find("a")
        .prop("href"),
      `/couponcodes/${newCoupon.id}`
    )
    assert.equal(
      wrapper.find(".coupon-success-div").text(),
      `Download coupon codes for "${newCoupon.payment.name}"`
    )
  })

  it("sets state.created to true if submission is successful", async () => {
    const testCouponData = { products: [products[0]] }
    const createCouponStub = sandbox
      .stub()
      .returns({ transformed: makeCouponPaymentVersion() })
    const instance = renderCreateCouponPage({
      createCoupon: createCouponStub
    }).instance()
    await instance.onSubmit(testCouponData, {
      setSubmitting: setSubmittingStub,
      setErrors:     setErrorsStub
    })
    sinon.assert.calledWith(createCouponStub, {
      product_ids: [products[0].id],
      ...testCouponData
    })
    sinon.assert.calledWith(setSubmittingStub, false)
    assert.isTrue(instance.state.created)
  })

  it("sets state.created to false and sets errors if submission is unsuccessful", async () => {
    const testCouponData = { products: [] }
    const createCouponStub = sandbox.stub().returns({
      body: {
        errors: [
          { products: "Must select a product" },
          { name: "Must be unique" }
        ]
      }
    })
    const instance = renderCreateCouponPage({
      createCoupon: createCouponStub
    }).instance()
    await instance.onSubmit(testCouponData, {
      setSubmitting: setSubmittingStub,
      setErrors:     setErrorsStub
    })
    sinon.assert.calledWith(createCouponStub, testCouponData)
    sinon.assert.calledWith(setSubmittingStub, false)
    sinon.assert.calledWith(setErrorsStub, {
      products: "Must select a product",
      name:     "Must be unique"
    })
    assert.isFalse(instance.state.created)
  })

  it("toggleCouponType() changes state.isPromo", async () => {
    const instance = renderCreateCouponPage().instance()
    assert.isFalse(instance.state.isPromo)
    await instance.toggleCouponType()
    assert.isTrue(instance.state.isPromo)
    await instance.toggleCouponType()
    assert.isFalse(instance.state.isPromo)
  })

  it("toggleProductType() clears selectedProducts and sets product type", async () => {
    const instance = renderCreateCouponPage().instance()
    await instance.setState({ selectedProducts: [products[0].id] })
    assert.deepEqual(instance.state.selectedProducts, [products[0].id])
    assert.equal(instance.state.productType, "courserun")
    instance.toggleProductType({ target: { value: "program" } })
    assert.equal(instance.state.productType, "program")
    assert.deepEqual(instance.state.selectedProducts, [])
  })

  //
  ;["courserun", "program", "course"].forEach(productType => {
    it(`filterProducts() correctly filters products by product type ${productType}`, async () => {
      const instance = renderCreateCouponPage().instance()
      await instance.setState({ productType })
      const filteredProducts = instance.filterProducts()
      assert.equal(filteredProducts.length, 1)
      filteredProducts.forEach(product => {
        assert.equal(product.product_type, productType)
        assert.isTrue(products.includes(product))
      })
    })
  })

  it("selectProducts() correctly sets state.products", () => {
    const wrapper = renderCreateCouponPage()
    const selectedProducts = [products[1], products[2]]
    wrapper.instance().selectProducts(selectedProducts)
    assert.deepEqual(
      wrapper.instance().state.selectedProducts,
      selectedProducts
    )
  })

  it("clearSuccess() changes state.created and clears state.selectedProducts", () => {
    const instance = renderCreateCouponPage().instance()
    instance.setState({ created: true, products: products })
    instance.clearSuccess()
    assert.isFalse(instance.state.created)
    assert.deepEqual(instance.state.selectedProducts, [])
  })
})
