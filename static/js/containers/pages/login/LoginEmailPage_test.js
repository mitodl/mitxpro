// @flow
import { assert } from "chai"
import sinon from "sinon"

import LoginEmailPage, {
  LoginEmailPage as InnerLoginEmailPage
} from "./LoginEmailPage"
import IntegrationTestHelper from "../../../util/integration_test_helper"
import {
  STATE_LOGIN_PASSWORD,
  STATE_ERROR,
  STATE_REGISTER_REQUIRED
} from "../../../lib/auth"
import { makeLoginAuthResponse } from "../../../factories/auth"
import { routes } from "../../../lib/urls"

describe("LoginEmailPage", () => {
  const email = "email@example.com"
  let helper, renderPage, setSubmittingStub, setErrorsStub

  beforeEach(() => {
    helper = new IntegrationTestHelper()

    setSubmittingStub = helper.sandbox.stub()
    setErrorsStub = helper.sandbox.stub()

    renderPage = helper.configureHOCRenderer(
      LoginEmailPage,
      InnerLoginEmailPage,
      {},
      {
        location: {
          search: "?next=/checkout/product=1"
        }
      }
    )
  })

  afterEach(() => {
    helper.cleanup()
  })

  it("displays a form", async () => {
    const { inner } = await renderPage()

    assert.ok(inner.find("EmailForm").exists())
  })

  it("next query parameter exists in create account link", async () => {
    const { inner } = await renderPage()

    assert.ok(
      inner
        .find(`Link[to='${routes.register.begin}?next=/checkout/product=1']`)
        .exists()
    )
  })

  //
  ;[STATE_ERROR, STATE_REGISTER_REQUIRED].forEach(state => {
    it(`handles onSubmit by calling setErrors given state=${state}`, async () => {
      const { inner } = await renderPage()
      const fieldErrors = {
        email: "error message"
      }

      helper.handleRequestStub.returns({
        body: makeLoginAuthResponse({
          state,
          field_errors: fieldErrors
        })
      })

      const onSubmit = inner.find("EmailForm").prop("onSubmit")

      await onSubmit(
        { email },
        { setSubmitting: setSubmittingStub, setErrors: setErrorsStub }
      )

      assert.lengthOf(helper.browserHistory, 1)
      sinon.assert.calledWith(setErrorsStub, fieldErrors)
      sinon.assert.calledWith(setSubmittingStub, false)
    })
  })

  it("handles onSubmit for an existing user password login", async () => {
    const { inner } = await renderPage()

    helper.handleRequestStub.returns({
      body: makeLoginAuthResponse({
        state: STATE_LOGIN_PASSWORD
      })
    })

    const onSubmit = inner.find("EmailForm").prop("onSubmit")

    await onSubmit(
      { email },
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
})
