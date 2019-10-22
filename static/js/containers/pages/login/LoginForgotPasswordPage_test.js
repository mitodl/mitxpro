// @flow
/* global SETTINGS: false */
import { assert } from "chai"
import sinon from "sinon"

import LoginForgotPasswordPage, {
  LoginForgotPasswordPage as InnerLoginForgotPasswordPage
} from "./LoginForgotPasswordPage"
import IntegrationTestHelper from "../../../util/integration_test_helper"
import { routes } from "../../../lib/urls"
import { ALERT_TYPE_TEXT } from "../../../constants"

describe("LoginForgotPasswordPage", () => {
  const email = "email@example.com"
  const supportEmail = "email@localhost"
  let helper, renderPage, setSubmittingStub

  beforeEach(() => {
    SETTINGS.support_email = supportEmail
    helper = new IntegrationTestHelper()

    setSubmittingStub = helper.sandbox.stub()

    renderPage = helper.configureHOCRenderer(
      LoginForgotPasswordPage,
      InnerLoginForgotPasswordPage,
      {},
      {}
    )
  })

  afterEach(() => {
    helper.cleanup()
  })

  it("displays a form", async () => {
    const { inner } = await renderPage()

    assert.ok(inner.find("EmailForm").exists())
  })

  it("handles onSubmit", async () => {
    const { inner, store } = await renderPage()

    helper.handleRequestStub.returns({
      status: 200
    })

    const onSubmit = inner.find("EmailForm").prop("onSubmit")

    await onSubmit({ email }, { setSubmitting: setSubmittingStub })

    sinon.assert.calledWith(
      helper.handleRequestStub,
      "/api/password_reset/",
      "POST",
      {
        body: {
          email
        },
        credentials: undefined,
        headers:     { "X-CSRFTOKEN": null }
      }
    )

    assert.lengthOf(helper.browserHistory, 2)
    assert.include(helper.browserHistory.location, {
      pathname: routes.root,
      search:   ""
    })
    sinon.assert.calledWith(setSubmittingStub, false)
  })

  it("after submit it remains on the forgot password page", async () => {
    const { inner } = await renderPage()
    const onSubmit = inner.find("EmailForm").prop("onSubmit")
    await onSubmit({ email }, { setSubmitting: setSubmittingStub })
    assert.isNotTrue(inner.find("EmailForm").exists())
  })

  it("contains the customer support link", async () => {
    const { inner } = await renderPage()
    const onSubmit = inner.find("EmailForm").prop("onSubmit")
    await onSubmit({ email }, { setSubmitting: setSubmittingStub })
    assert.equal(
      inner.find(".contact-support > a").prop("href"),
      `mailto:${supportEmail}`
    )
  })

  it("contains the reset your password link", async () => {
    const { inner } = await renderPage()
    const onSubmit = inner.find("EmailForm").prop("onSubmit")
    await onSubmit({ email }, { setSubmitting: setSubmittingStub })
    assert.equal(inner.find("li > Link").prop("to"), routes.login.forgot.begin)
  })
})
