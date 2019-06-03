// @flow
import { assert } from "chai"
import sinon from "sinon"

import CheckoutPage, {
  CheckoutPage as InnerCheckoutPage,
  calcSelectedRunIds
} from "./CheckoutPage"
import * as formFuncs from "../../lib/form"
import IntegrationTestHelper from "../../util/integration_test_helper"
import {
  makeBasketResponse,
  makeCouponSelection
} from "../../factories/ecommerce"
import {
  calculateDiscount,
  calculatePrice,
  formatPrice,
  formatRunTitle
} from "../../lib/ecommerce"
import { assertRaises } from "../../lib/util"
import { PRODUCT_TYPE_COURSERUN, PRODUCT_TYPE_PROGRAM } from "../../constants"

describe("CheckoutPage", () => {
  let helper, renderPage, basket

  beforeEach(() => {
    basket = makeBasketResponse(PRODUCT_TYPE_PROGRAM)

    helper = new IntegrationTestHelper()
    renderPage = helper.configureHOCRenderer(
      CheckoutPage,
      InnerCheckoutPage,
      {
        entities: {
          basket
        }
      },
      {
        location: {}
      }
    )
  })

  afterEach(() => {
    helper.cleanup()
  })
  ;[true, false].forEach(hasCoupon => {
    it(`shows your basket ${
      hasCoupon ? "with" : "without"
    } a coupon`, async () => {
      const basketItem = basket.items[0]
      basketItem.type = "program"
      const coupon = makeCouponSelection()
      basket.coupons = [coupon]
      if (hasCoupon) {
        coupon.targets = [basketItem.id]
      } else {
        coupon.targets = [-123]
      }
      const { inner } = await renderPage()
      assert.equal(inner.find(".item-type").text(), "Program")
      assert.equal(
        inner.find(".header .description").text(),
        basketItem.description
      )
      assert.equal(inner.find(".item-row").length, basketItem.courses.length)
      basketItem.courses.forEach((course, i) => {
        const courseRow = inner.find(".item-row").at(i)
        assert.equal(courseRow.find("img").prop("src"), course.thumbnail_url)
        assert.equal(courseRow.find("img").prop("alt"), course.title)
        assert.equal(courseRow.find(".title").text(), course.title)
      })
      assert.equal(
        inner.find(".price-row").text(),
        `Price:${formatPrice(basketItem.price)}`
      )

      if (hasCoupon) {
        assert.equal(
          inner.find(".discount-row").text(),
          `Discount:${formatPrice(calculateDiscount(basketItem, coupon))}`
        )
      } else {
        assert.isFalse(inner.find(".discount-row").exists())
      }

      assert.equal(
        inner.find(".total-row").text(),
        `Total:${formatPrice(calculatePrice(basketItem, coupon))}`
      )
    })
  })

  it("renders a course run basket item", async () => {
    basket = makeBasketResponse(PRODUCT_TYPE_COURSERUN)
    const basketItem = basket.items[0]
    basketItem.type = "courserun"

    const { inner } = await renderPage({
      entities: {
        basket
      }
    })

    assert.equal(inner.find(".item-type").text(), "Course")
    assert.equal(inner.find(".item-row").length, 1)

    const courseRow = inner.find(".item-row").at(0)
    assert.equal(
      courseRow.find("img").prop("src"),
      basketItem.courses[0].thumbnail_url
    )
    assert.equal(courseRow.find("img").prop("alt"), basketItem.courses[0].title)
    assert.equal(
      courseRow.find(".item-row .title").text(),
      basketItem.courses[0].title
    )
  })
  ;[true, false].forEach(hasError => {
    it(`updates the basket with a product id from the query parameter${
      hasError ? ", but an error is returned" : ""
    }`, async () => {
      const productId = 4567
      if (hasError) {
        helper.handleRequestStub.withArgs("/api/basket/", "PATCH").returns({
          status: 400,
          body:   {
            errors: "error"
          }
        })
      }
      const { inner } = await renderPage(
        {},
        {
          location: {
            search: `product=${productId}`
          }
        }
      )

      sinon.assert.calledWith(
        helper.handleRequestStub,
        "/api/basket/",
        "PATCH",
        {
          body:        { items: [{ id: productId }] },
          credentials: undefined,
          headers:     {
            "X-CSRFTOKEN": null
          }
        }
      )
      assert.equal(inner.state().errors, hasError ? "error" : null)
    })
  })

  describe("mount", () => {
    const productError = "product error",
      couponError = "coupon error",
      couponCode = "codeforcoupon",
      productId = 12345
    let couponPayload, productPayload

    beforeEach(() => {
      couponPayload = {
        body:        { coupons: [{ code: couponCode }] },
        credentials: undefined,
        headers:     {
          "X-CSRFTOKEN": null
        }
      }
      productPayload = {
        body:        { items: [{ id: productId }] },
        credentials: undefined,
        headers:     {
          "X-CSRFTOKEN": null
        }
      }
    })
    ;[
      [true, false, couponError],
      [true, true, null],
      [false, false, productError],
      [false, true, productError]
    ].forEach(([hasValidProductId, hasValidCoupon, expError]) => {
      it(`updates the basket with a ${
        hasValidProductId ? "" : "in"
      }valid product id and a ${
        hasValidCoupon ? "" : "in"
      }valid coupon code from the query parameter`, async () => {
        if (!hasValidProductId) {
          helper.handleRequestStub
            .withArgs("/api/basket/", "PATCH", productPayload)
            .returns({
              status: 400,
              body:   {
                errors: "product error"
              }
            })
        }
        if (!hasValidCoupon) {
          helper.handleRequestStub
            .withArgs("/api/basket/", "PATCH", couponPayload)
            .returns({
              status: 400,
              body:   {
                errors: "coupon error"
              }
            })
        }
        const { inner } = await renderPage(
          {},
          {
            location: {
              search: `product=${productId}&code=${couponCode}`
            }
          }
        )
        // wait for componentDidMount to resolve
        await Promise.resolve()
        sinon.assert.calledWith(
          helper.handleRequestStub,
          "/api/basket/",
          "PATCH",
          productPayload
        )
        assert.equal(
          helper.handleRequestStub.calledWith(
            "/api/basket/",
            "PATCH",
            couponPayload
          ),
          hasValidProductId
        )

        assert.equal(inner.state().errors, expError)
      })
    })
  })

  it("displays the coupon code", async () => {
    const { inner } = await renderPage()
    const couponCode = "a coupon code"
    inner.setState({
      couponCode
    })
    inner.update()
    assert.equal(inner.find(".coupon-code-row input").prop("value"), couponCode)
  })

  it("updates the coupon code", async () => {
    const { inner } = await renderPage()
    const couponCode = "a coupon code"
    const event = {
      target: {
        value: couponCode
      },
      preventDefault: helper.sandbox.stub()
    }
    inner.find(".coupon-code-row input").prop("onChange")(event)
    assert.equal(inner.state().couponCode, couponCode)
  })

  //
  ;[true, false].forEach(hasCouponCode => {
    it(`${hasCouponCode ? "submits" : "clears"} the coupon code`, async () => {
      const { inner } = await renderPage()
      const couponCode = "code"
      inner.setState({
        couponCode: hasCouponCode ? couponCode : ""
      })

      inner.find("form").prop("onSubmit")({
        preventDefault: helper.sandbox.stub()
      })
      sinon.assert.calledWith(
        helper.handleRequestStub,
        "/api/basket/",
        "PATCH",
        {
          body:    { coupons: hasCouponCode ? [{ code: couponCode }] : [] },
          headers: {
            "X-CSRFTOKEN": null
          },
          credentials: undefined
        }
      )
    })
  })

  it("submits the coupon code currently in the basket if there is none in the state", async () => {
    const { inner } = await renderPage()
    const code = basket.coupons[0].code
    await inner.find(".apply-button").prop("onClick")({
      preventDefault: helper.sandbox.stub()
    })
    sinon.assert.calledWith(helper.handleRequestStub, "/api/basket/", "PATCH", {
      body:        { coupons: [{ code: code }] },
      credentials: undefined,
      headers:     {
        "X-CSRFTOKEN": null
      }
    })
  })

  it("clears the state after submitting the basket", async () => {
    const { inner } = await renderPage()
    const couponCode = "coupon code"
    inner.setState({
      errors:       "errors",
      selectedRuns: ["runs"],
      couponCode:   couponCode
    })
    await inner.find(".apply-button").prop("onClick")({
      preventDefault: helper.sandbox.stub()
    })
    sinon.assert.calledWith(helper.handleRequestStub, "/api/basket/", "PATCH", {
      body:        { coupons: [{ code: couponCode }] },
      credentials: undefined,
      headers:     {
        "X-CSRFTOKEN": null
      }
    })
    assert.deepEqual(inner.state(), {
      couponCode:   null,
      errors:       null,
      selectedRuns: null
    })
  })

  it("tries to submit the coupon code but receives an error message", async () => {
    const { inner } = await renderPage()
    const errors = "Unknown error"
    helper.handleRequestStub.withArgs("/api/basket/", "PATCH").returns({
      status: 400,
      body:   {
        errors
      }
    })
    await assertRaises(async () => {
      await inner.find("form").prop("onSubmit")({
        preventDefault: helper.sandbox.stub()
      })
    }, "Received error from request")

    assert.equal(inner.state().errors, errors)
    assert.equal(inner.find(".enrollment-input .error").text(), "Unknown error")
    assert.isTrue(inner.find(".enrollment-input input.error-border").exists())
  })

  it("checks out", async () => {
    const { inner } = await renderPage()

    const url = "/api/checkout/"
    const payload = { pay: "load" }
    helper.handleRequestStub.withArgs("/api/checkout/", "POST").returns({
      body: {
        url,
        payload
      }
    })
    const submitStub = helper.sandbox.stub()
    const form = document.createElement("form")
    // $FlowFixMe: need to overwrite this function to mock it
    form.submit = submitStub
    const createFormStub = helper.sandbox
      .stub(formFuncs, "createCyberSourceForm")
      .returns(form)
    await inner.find(".checkout-button").prop("onClick")()
    sinon.assert.calledWith(createFormStub, url, payload)
    sinon.assert.calledWith(submitStub)
    sinon.assert.calledWith(
      helper.handleRequestStub,
      "/api/checkout/",
      "POST",
      {
        body:    undefined,
        headers: {
          "X-CSRFTOKEN": null
        },
        credentials: undefined
      }
    )

    const basketItem = basket.items[0]
    sinon.assert.calledWith(helper.handleRequestStub, "/api/basket/", "PATCH", {
      body: {
        items: [
          {
            id:      basketItem.product_id,
            run_ids: Object.values(
              inner.instance().getSelectedRunIds(basketItem)
            )
          }
        ]
      },
      headers: {
        "X-CSRFTOKEN": null
      },
      credentials: undefined
    })
  })

  it("checks out and redirects to a location instead of submitting a form", async () => {
    const { inner } = await renderPage()

    const url = "/a/b/c/"
    const payload = { pay: "load" }
    helper.handleRequestStub.withArgs("/api/checkout/", "POST").returns({
      body: {
        url,
        payload,
        method: "GET"
      }
    })
    const submitStub = helper.sandbox.stub()
    const form = document.createElement("form")
    // $FlowFixMe: need to overwrite this function to mock it
    form.submit = submitStub
    await inner.find(".checkout-button").prop("onClick")()

    const basketItem = basket.items[0]
    sinon.assert.calledWith(helper.handleRequestStub, "/api/basket/", "PATCH", {
      body: {
        items: [
          {
            id:      basketItem.product_id,
            run_ids: Object.values(
              inner.instance().getSelectedRunIds(basketItem)
            )
          }
        ]
      },
      headers: {
        "X-CSRFTOKEN": null
      },
      credentials: undefined
    })
    assert.isTrue(window.location.toString().endsWith(url))
  })

  it("fails to check out because basket API failed to validate", async () => {
    const { inner } = await renderPage()
    const errors = ["something went wrong"]

    helper.handleRequestStub.withArgs("/api/basket/", "PATCH").returns({
      status: 400,
      body:   {
        errors
      }
    })
    const submitStub = helper.sandbox.stub()
    const form = document.createElement("form")
    // $FlowFixMe: need to overwrite this function to mock it
    form.submit = submitStub

    await assertRaises(async () => {
      await inner.find(".checkout-button").prop("onClick")()
    }, "Received error from request")
    assert.deepEqual(inner.state().errors, errors)
  })

  it("fails to check out because checkout API failed to validate", async () => {
    const { inner } = await renderPage()

    const errors = ["some error"]
    helper.handleRequestStub.withArgs("/api/checkout/", "POST").returns({
      status: 400,
      body:   {
        errors
      }
    })
    const submitStub = helper.sandbox.stub()
    const form = document.createElement("form")
    // $FlowFixMe: need to overwrite this function to mock it
    form.submit = submitStub
    await assertRaises(async () => {
      await inner.find(".checkout-button").prop("onClick")()
    }, "Received error from request")
  })

  it("gets selected runs", async () => {
    const { inner } = await renderPage()
    const item = {
      courses: [
        {
          id:         "course_1",
          courseruns: [
            {
              id: "run_1a"
            },
            {
              id: "run_1b"
            }
          ]
        },
        {
          id:         "course_2",
          courseruns: [
            {
              id: "run_2a"
            },
            {
              id: "run_2b"
            }
          ]
        }
      ],
      run_ids: ["run_2a", "run_1b"],
      price:   "123.45"
    }
    // $FlowFixMe
    basket.items = [item]
    inner.setState({
      selectedRuns: {
        course_3: "run_3",
        course_2: "run_2b"
      }
    })

    assert.deepEqual(inner.instance().getSelectedRunIds(item), {
      course_1: "run_1b",
      course_2: "run_2b",
      course_3: "run_3"
    })
  })

  it("does show a select for course run product", async () => {
    basket.items[0].type = PRODUCT_TYPE_COURSERUN
    const { inner } = await renderPage()
    const firstCourse = inner.find(".item-row").at(0)
    assert.equal(firstCourse.find("select").length, 1)
  })

  it("shows a select with options for a program product, and updates a run", async () => {
    const item = basket.items[0]
    const { inner } = await renderPage()
    assert.equal(inner.find("select").length, basket.items[0].courses.length)
    item.courses.forEach((course, i) => {
      const courseRow = inner.find(".item-row").at(i)
      assert.equal(courseRow.find(".title").text(), course.title)

      const select = inner.find("select").at(i)

      const runId = calcSelectedRunIds(item)[course.id]
      assert.equal(select.prop("value"), runId || "")

      const runs = course.courseruns
      assert.equal(select.find("option").length, runs.length + 1)
      const firstOption = select.find("option").at(0)
      assert.equal(firstOption.prop("value"), null)
      assert.equal(firstOption.text(), "Select a course run")

      select.prop(select.prop("onChange")({ target: { value: "345" } }))
      assert.equal(inner.state().selectedRuns[course.id], 345)

      runs.forEach((run, j) => {
        const runOption = select.find("option").at(j + 1)
        assert.equal(runOption.prop("value"), run.id)
        assert.equal(runOption.text(), formatRunTitle(run))
      })
    })
  })

  it("displays no items if there are none in the basket", async () => {
    basket.items = []
    const { inner } = await renderPage()
    assert.equal(inner.text(), "No item in basket")
  })
})
