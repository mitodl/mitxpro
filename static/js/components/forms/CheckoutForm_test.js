// @flow
/* global SETTINGS: false */
import { mount, shallow } from "enzyme/build"
import React from "react"
import { assert } from "chai"
import sinon from "sinon"
import { Formik, Field } from "formik"
import { Modal, ModalHeader } from "reactstrap"

import { CheckoutForm, InnerCheckoutForm } from "./CheckoutForm"
import Markdown from "../Markdown"

import { makeBasketResponse } from "../../factories/ecommerce"
import {
  calculateDiscount,
  calculatePrice,
  formatPrice,
  formatRunTitle,
  calcSelectedRunIds
} from "../../lib/ecommerce"
import { PRODUCT_TYPE_COURSERUN, PRODUCT_TYPE_PROGRAM } from "../../constants"
import { isIf, shouldIf } from "../../lib/test_utils"

describe("CheckoutForm", () => {
  let sandbox,
    onSubmitStub,
    basket,
    coupon,
    couponCode,
    basketItem,
    submitCouponStub,
    updateProductStub

  beforeEach(() => {
    basket = makeBasketResponse()
    basketItem = basket.items[0]
    coupon = basket.coupons[0]
    couponCode = "asdf"
    sandbox = sinon.createSandbox()
    onSubmitStub = sandbox.stub()
    submitCouponStub = sandbox.stub()
    updateProductStub = sandbox.stub()
    SETTINGS.zendesk_config = {
      help_widget_enabled: false,
      help_widget_key:     "fake_key"
    }
  })

  afterEach(() => {
    sandbox.restore()
  })

  const renderForm = (props = {}) =>
    mount(
      <CheckoutForm
        onSubmit={onSubmitStub}
        coupon={coupon}
        couponCode={couponCode}
        basket={basket}
        requestPending={false}
        item={basketItem}
        submitCoupon={submitCouponStub}
        selectedRuns={{}}
        updateProduct={updateProductStub}
        {...props}
      />
    )

  ;[true, false].forEach(hasCoupon => {
    it(`shows your basket ${
      hasCoupon ? "with" : "without"
    } a coupon`, async () => {
      basketItem.type = "program"
      const inner = await renderForm({
        coupon: hasCoupon ? coupon : null
      })
      assert.equal(inner.find(".item-type").text(), "Program")
      assert.equal(
        inner.find(".header .description").text(),
        basketItem.content_title
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
        `Total:${formatPrice(
          calculatePrice(basketItem, hasCoupon ? coupon : null)
        )}`
      )
    })
  })

  it("renders a course run basket item", async () => {
    basketItem.type = PRODUCT_TYPE_COURSERUN

    const inner = await renderForm()

    assert.equal(inner.find(".item-type").text(), "Course")
    assert.equal(inner.find(".item-row").length, 1)
    assert.equal(inner.find("img").prop("src"), basketItem.thumbnail_url)
    assert.equal(inner.find("img").prop("alt"), basketItem.content_title)
    assert.equal(
      inner.find(".item-row .title").text(),
      basketItem.content_title
    )
  })

  //
  ;[true, false].forEach(hasRuns => {
    it(`validates ${hasRuns ? "existing" : "present"} runs`, async () => {
      basketItem.type = PRODUCT_TYPE_PROGRAM
      const runs = {}
      if (hasRuns) {
        for (const course of basketItem.courses) {
          runs[course.id] = course.courseruns[0].id
        }
      }
      const inner = await renderForm({
        selectedRuns: runs
      })
      const errors = inner.find(Formik).prop("validate")({ runs })

      assert.equal(
        errors.runs,
        hasRuns
          ? undefined
          : `No run selected for ${basketItem.courses
            .map(course => course.title)
            .join(", ")}`
      )
    })
  })

  //
  ;[
    [true, true, false],
    [true, false, true],
    [false, true, false],
    [false, false, false]
  ].forEach(([hasDataConsent, checkedDataConsent, shouldHaveError]) => {
    it(`validates data consent ${
      hasDataConsent ? "with" : "without"
    } an agreement, when the user ${
      checkedDataConsent ? "has" : "hasn't"
    } checked the box`, async () => {
      if (!hasDataConsent) {
        basket.data_consents = []
      }
      const inner = await renderForm()
      const errors = inner.find(Formik).prop("validate")({
        dataConsent: checkedDataConsent,
        runs:        {}
      })
      assert.equal(
        errors.data_consents,
        shouldHaveError
          ? "User must consent to the Data Sharing Policy to use the coupon."
          : undefined
      )
    })
  })

  it("shows the data consent validation error", async () => {
    const errorMessage = "my custom error message"
    const inner = await shallow(
      // $FlowFixMe
      <InnerCheckoutForm
        basket={basket}
        item={basketItem}
        values={{ dataConsent: false }}
        errors={{ data_consents: errorMessage }}
        onMount={sandbox.stub()}
      />
    )
    assert.equal(inner.find(".data-consent .error").text(), errorMessage)
  })

  //
  ;[true, false].forEach(hasQueryParam => {
    it(`displays the coupon code${
      hasQueryParam ? " from a query parameter" : " from the coupon object"
    }`, async () => {
      const inner = await renderForm({
        couponCode: hasQueryParam ? couponCode : ""
      })
      inner.update()
      assert.equal(
        inner.find(".coupon-code-row input").prop("value"),
        hasQueryParam ? couponCode : coupon.code
      )
    })
  })

  it("loads the coupon code on mount", async () => {
    await renderForm()
    sinon.assert.calledWith(submitCouponStub, couponCode)
  })

  it("does not load the coupon code if there is none", async () => {
    await renderForm({ couponCode: "" })
    sinon.assert.notCalled(submitCouponStub)
  })

  it("loads the coupon code even if there are spaces around the coupon", async () => {
    const couponCode = "  xyz  "
    await renderForm({ couponCode: couponCode })
    sinon.assert.calledWith(submitCouponStub, couponCode)
  })

  it("does not load the coupon code if the code matches the coupon already in the basket", async () => {
    await renderForm({ couponCode: basket.coupons[0].code })
    sinon.assert.notCalled(submitCouponStub)
  })

  //
  ;[true, false].forEach(hasCouponCode => {
    it(`${
      hasCouponCode ? "submits" : "clears"
    } the coupon code after the apply button is clicked`, async () => {
      const inner = await renderForm({
        couponCode: hasCouponCode ? couponCode : "",
        coupon:     hasCouponCode ? coupon : null
      })
      submitCouponStub.reset()

      inner.find(".apply-button").prop("onClick")()
      sinon.assert.calledWith(submitCouponStub, hasCouponCode ? couponCode : "")
    })

    it(`${
      hasCouponCode ? "submits" : "clears"
    } the coupon code after the enter key is pressed`, async () => {
      const inner = await renderForm({
        couponCode: hasCouponCode ? couponCode : "",
        coupon:     hasCouponCode ? coupon : null
      })
      submitCouponStub.reset()

      inner.find("input.coupon-code-entry").prop("onKeyDown")({
        key:            "Enter",
        preventDefault: sandbox.stub()
      })
      sinon.assert.calledWith(submitCouponStub, hasCouponCode ? couponCode : "")
    })
  })

  it("does not do anything special if a key that's not Enter is pressed in the coupon code box", async () => {
    const inner = await renderForm()
    submitCouponStub.reset()
    inner.find("input.coupon-code-entry").prop("onKeyDown")({
      key: "x"
    })
    sinon.assert.notCalled(submitCouponStub)
  })
  ;[PRODUCT_TYPE_COURSERUN, PRODUCT_TYPE_PROGRAM].forEach(type => {
    it(`shows a select with options for a product, and updates a ${type} run`, async () => {
      basketItem.type = type
      if (type === PRODUCT_TYPE_COURSERUN) {
        basketItem.courses = [basketItem.courses[0]]
      }
      const selectedRuns = calcSelectedRunIds(basketItem)
      const inner = await renderForm({
        selectedRuns
      })
      assert.equal(inner.find("select").length, basketItem.courses.length)
      basketItem.courses.forEach((course, i) => {
        const select = inner.find("select").at(i)

        const runs = course.courseruns
        assert.equal(select.find("option").length, runs.length + 1)
        const firstOption = select.find("option").at(0)
        assert.equal(firstOption.prop("value"), "")
        assert.equal(firstOption.text(), "Select a course run")

        runs.forEach((run, j) => {
          const runOption = select.find("option").at(j + 1)
          assert.equal(runOption.prop("value"), run.id)
          assert.equal(runOption.text(), formatRunTitle(run))
        })
      })
    })
  })

  it("updates the product when the course run select is changed", async () => {
    basketItem.type = PRODUCT_TYPE_COURSERUN
    basketItem.courses = [basketItem.courses[0]]
    const run = basketItem.courses[0].courseruns[1]
    const resetFormStub = sandbox.stub()

    const inner = await shallow(
      // $FlowFixMe
      <InnerCheckoutForm
        onSubmit={onSubmitStub}
        basket={basket}
        errors={{}}
        item={basketItem}
        onMount={sandbox.stub()}
        setValues={sandbox.stub()}
        resetForm={resetFormStub}
        updateProduct={updateProductStub}
        values={{}}
      />
    )

    await inner
      .find("FormikConnect(FieldInner)[component='select']")
      .prop("onChange")({ target: { value: String(run.id) } })
    sinon.assert.calledWith(updateProductStub, run.product_id, run.id)
    sinon.assert.calledWith(resetFormStub)
  })

  //
  ;[true, false].forEach(hasDataConsent => {
    it(`${
      hasDataConsent ? "has" : "doesn't have"
    } a data consent checkbox`, async () => {
      if (!hasDataConsent) {
        basket.data_consents = []
      }

      const inner = await renderForm()
      assert.equal(
        inner.find(".data-consent-row").length,
        hasDataConsent ? 1 : 0
      )
      if (hasDataConsent) {
        const expected = `*By checking this box, I give my consent to MIT to disclose data to ${
          basket.data_consents[0].company.name
        }.`
        assert.isTrue(inner.text().includes(expected))
      }
    })
  })

  it("passes the appropriate checked value for the the data consent checkbox", async () => {
    for (const checked of [true, false]) {
      const inner = shallow(
        // $FlowFixMe
        <InnerCheckoutForm
          onSubmit={onSubmitStub}
          basket={basket}
          errors={{}}
          item={basketItem}
          onMount={sandbox.stub()}
          updateProduct={updateProductStub}
          values={{
            dataConsent: checked
          }}
        />
      )
      assert.equal(
        inner
          .find(".data-consent-row")
          .find(Field)
          .prop("checked"),
        checked
      )
    }
  })

  it("toggles the data consent modal", async () => {
    const inner = shallow(
      // $FlowFixMe
      <InnerCheckoutForm
        onSubmit={onSubmitStub}
        basket={basket}
        errors={{}}
        item={basketItem}
        onMount={sandbox.stub()}
        updateProduct={updateProductStub}
        values={{}}
      />
    )
    const toggle = inner.find(".data-consent-row a").prop("onClick")
    assert.isFalse(inner.state().dataSharingModalVisibility)
    toggle()
    assert.isTrue(inner.state().dataSharingModalVisibility)
    toggle()
    assert.isFalse(inner.state().dataSharingModalVisibility)
  })
  ;[true, false].forEach(hasDataConsent => {
    [true, false].forEach(modalVisible => {
      it(`${
        hasDataConsent ? "has" : "doesn't have"
      } the data consent modal and the modal is ${
        modalVisible ? "" : "in"
      }visible`, async () => {
        if (!hasDataConsent) {
          basket.data_consents = []
        }
        const inner = shallow(
          // $FlowFixMe
          <InnerCheckoutForm
            onSubmit={onSubmitStub}
            basket={basket}
            errors={{}}
            item={basketItem}
            onMount={sandbox.stub()}
            updateProduct={updateProductStub}
            values={{}}
          />
        )
        inner.setState({ dataSharingModalVisibility: modalVisible })

        if (!hasDataConsent) {
          assert.isFalse(inner.find(Modal).exists())
        } else {
          assert.equal(inner.find(Modal).prop("isOpen"), modalVisible)
          inner.find(Modal).prop("toggle")()
          assert.equal(inner.state().dataSharingModalVisibility, !modalVisible)
          inner.find(ModalHeader).prop("toggle")()
          assert.equal(inner.state().dataSharingModalVisibility, modalVisible)
          assert.equal(
            inner.find(Markdown).prop("source"),
            basket.data_consents[0].consent_text
          )
        }
      })
    })
  })

  it("has links to the privacy policy, terms of service, and the honor code", async () => {
    const inner = await renderForm()

    const linkPairs = [
      ["Terms of Service", "/terms-of-service/"],
      ["Refund Policy", "/honor-code/"],
      ["Privacy Policy", "/privacy-policy/"]
    ]

    inner.find(".submit-links a").forEach((linkWrapper, i) => {
      const [text, url] = linkPairs[i]
      assert.equal(linkWrapper.text(), text)
      assert.equal(linkWrapper.prop("href"), url)
    })
  })

  //
  ;[true, false].forEach(requestPending => {
    it(`${shouldIf(
      requestPending
    )} disable submit buttons while the request ${isIf(
      requestPending
    )} in progress`, async () => {
      const inner = await renderForm({
        requestPending
      })

      assert.equal(
        inner.find(".checkout-button").prop("disabled"),
        requestPending
      )
      assert.equal(inner.find(".apply-button").prop("disabled"), requestPending)
    })
  })
})
