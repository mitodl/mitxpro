// @flow
import { assert } from "chai"
import sinon from "sinon"

import RegisterEmailPage, {
  RegisterEmailPage as InnerRegisterEmailPage
} from "./RegisterEmailPage"
import IntegrationTestHelper from "../../../util/integration_test_helper"
import {
  STATE_REGISTER_CONFIRM_SENT,
  STATE_LOGIN_PASSWORD,
  STATE_ERROR
} from "../../../lib/auth"
import { routes } from "../../../lib/urls"

describe("RegisterEmailPage", () => {
  const email = "email@example.com"
  const recaptcha = "recaptchaTestValue"
  const partialToken = "partialTokenTestValue"
  let helper, renderPage, setSubmittingStub, setErrorsStub

  beforeEach(() => {
    helper = new IntegrationTestHelper()

    setSubmittingStub = helper.sandbox.stub()
    setErrorsStub = helper.sandbox.stub()

    renderPage = helper.configureHOCRenderer(
      RegisterEmailPage,
      InnerRegisterEmailPage,
      {},
      {
        location: {
          search: `partial_token=${partialToken}`
        }
      }
    )
  })

  afterEach(() => {
    helper.cleanup()
  })

  it("displays a form", async () => {
    const { inner } = await renderPage()

    assert.ok(inner.find("RegisterEmailForm").exists())
  })

  it("handles onSubmit for an error response", async () => {
    const { inner } = await renderPage()
    const error = "error message"

    helper.handleRequestStub.returns({
      body: {
        state:  STATE_ERROR,
        errors: [error]
      }
    })

    const onSubmit = inner.find("RegisterEmailForm").prop("onSubmit")

    await onSubmit(
      { email, recaptcha },
      { setSubmitting: setSubmittingStub, setErrors: setErrorsStub }
    )

    assert.lengthOf(helper.browserHistory, 1)
    sinon.assert.calledWith(setErrorsStub, {
      email: error
    })
    sinon.assert.calledWith(setSubmittingStub, false)
  })

  it("handles onSubmit for an existing user password login", async () => {
    const { inner } = await renderPage()

    helper.handleRequestStub.returns({
      body: {
        state:  STATE_LOGIN_PASSWORD,
        errors: []
      }
    })

    const onSubmit = inner.find("RegisterEmailForm").prop("onSubmit")

    await onSubmit(
      { email, recaptcha },
      { setSubmitting: setSubmittingStub, setErrors: setErrorsStub }
    )

    assert.lengthOf(helper.browserHistory, 2)
    assert.include(helper.browserHistory.location, {
      pathname: routes.login.password,
      search:   ""
    })
    sinon.assert.notCalled(setErrorsStub)
    sinon.assert.calledWith(setSubmittingStub, false)
  })

  it("handles onSubmit for a confirmation email", async () => {
    const { inner, store } = await renderPage()

    helper.handleRequestStub.returns({
      body: {
        state:  STATE_REGISTER_CONFIRM_SENT,
        errors: []
      }
    })

    const onSubmit = inner.find("RegisterEmailForm").prop("onSubmit")

    await onSubmit(
      { email, recaptcha },
      { setSubmitting: setSubmittingStub, setErrors: setErrorsStub }
    )

    assert.lengthOf(helper.browserHistory, 2)
    assert.include(helper.browserHistory.location, {
      pathname: routes.login.begin,
      search:   ""
    })
    sinon.assert.notCalled(setErrorsStub)
    sinon.assert.calledWith(setSubmittingStub, false)

    const { ui } = store.getState()

    assert.lengthOf(ui.userNotifications, 1)
    assert.include(
      ui.userNotifications,
      `We sent an email to ${email}. Please validate your address to continue.`
    )
  })
})
