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
import { makeRegisterAuthResponse } from "../../../factories/auth"
import { routes } from "../../../lib/urls"
import { ALERT_TYPE_TEXT } from "../../../constants"

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
    const fieldErrors = {
      email: "error message"
    }

    helper.handleRequestStub.returns({
      body: makeRegisterAuthResponse({
        state:        STATE_ERROR,
        field_errors: fieldErrors
      })
    })

    const onSubmit = inner.find("RegisterEmailForm").prop("onSubmit")

    await onSubmit(
      { email, recaptcha },
      { setSubmitting: setSubmittingStub, setErrors: setErrorsStub }
    )

    assert.lengthOf(helper.browserHistory, 1)
    sinon.assert.calledWith(setErrorsStub, fieldErrors)
    sinon.assert.calledWith(setSubmittingStub, false)
  })

  it("handles onSubmit for an existing user password login", async () => {
    const { inner, store } = await renderPage()

    helper.handleRequestStub.returns({
      body: makeRegisterAuthResponse({
        state: STATE_LOGIN_PASSWORD
      })
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

    const { ui } = store.getState()

    assert.deepEqual(ui.userNotifications, {
      "account-exists": {
        type:  ALERT_TYPE_TEXT,
        color: "danger",
        props: {
          text: `You already have an account with ${email}. Enter password to sign in.`
        }
      }
    })
  })

  it("handles onSubmit for a confirmation email", async () => {
    const { inner, store } = await renderPage()

    helper.handleRequestStub.returns({
      body: makeRegisterAuthResponse({
        state: STATE_REGISTER_CONFIRM_SENT
      })
    })

    const onSubmit = inner.find("RegisterEmailForm").prop("onSubmit")

    await onSubmit(
      { email, recaptcha },
      { setSubmitting: setSubmittingStub, setErrors: setErrorsStub }
    )

    assert.lengthOf(helper.browserHistory, 2)
    assert.include(helper.browserHistory.location, {
      pathname: routes.register.confirmSent,
      search:   `?email=${encodeURIComponent(email)}`
    })
    sinon.assert.notCalled(setErrorsStub)
    sinon.assert.calledWith(setSubmittingStub, false)
  })
})
