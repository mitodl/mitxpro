// @flow
import { assert } from "chai"
import sinon from "sinon"

import LoginPasswordPage, {
  LoginPasswordPage as InnerLoginPasswordPage
} from "./LoginPasswordPage"
import IntegrationTestHelper from "../../../util/integration_test_helper"
import {
  STATE_SUCCESS,
  STATE_ERROR,
  STATE_LOGIN_PASSWORD
} from "../../../lib/auth"
import { makeLoginAuthResponse } from "../../../factories/auth"
import { routes } from "../../../lib/urls"

describe("LoginPasswordPage", () => {
  const password = "abc123"
  let helper, renderPage, setSubmittingStub, setErrorsStub, auth

  beforeEach(() => {
    helper = new IntegrationTestHelper()

    setSubmittingStub = helper.sandbox.stub()
    setErrorsStub = helper.sandbox.stub()
    auth = makeLoginAuthResponse({
      state: STATE_LOGIN_PASSWORD
    })

    renderPage = helper.configureHOCRenderer(
      LoginPasswordPage,
      InnerLoginPasswordPage,
      {
        entities: {
          auth
        }
      },
      {}
    )
  })

  afterEach(() => {
    helper.cleanup()
  })

  it("displays a form", async () => {
    const { inner } = await renderPage()

    assert.ok(inner.find("LoginPasswordForm").exists())
  })

  it("handles onSubmit for an error response", async () => {
    const { inner } = await renderPage()
    const fieldErrors = {
      email: "error message"
    }

    helper.handleRequestStub.returns({
      body: makeLoginAuthResponse({
        state:        STATE_ERROR,
        field_errors: fieldErrors
      })
    })

    const onSubmit = inner.find("LoginPasswordForm").prop("onSubmit")

    await onSubmit(
      { password },
      { setSubmitting: setSubmittingStub, setErrors: setErrorsStub }
    )

    assert.lengthOf(helper.browserHistory, 1)
    sinon.assert.calledWith(setErrorsStub, fieldErrors)
    sinon.assert.calledWith(setSubmittingStub, false)
  })

  it("handles onSubmit success", async () => {
    const { inner } = await renderPage()

    helper.handleRequestStub.returns({
      body: makeLoginAuthResponse({
        state: STATE_SUCCESS
      })
    })

    const onSubmit = inner.find("LoginPasswordForm").prop("onSubmit")

    await onSubmit(
      { password },
      { setSubmitting: setSubmittingStub, setErrors: setErrorsStub }
    )

    assert.equal(window.location.href, `http://fake${routes.dashboard}`)
    sinon.assert.notCalled(setErrorsStub)
    sinon.assert.calledWith(setSubmittingStub, false)
  })
})
