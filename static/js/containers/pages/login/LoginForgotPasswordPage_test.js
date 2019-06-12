// @flow
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
  let helper, renderPage, setSubmittingStub

  beforeEach(() => {
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
        headers:     undefined
      }
    )

    assert.lengthOf(helper.browserHistory, 2)
    assert.include(helper.browserHistory.location, {
      pathname: routes.login.begin,
      search:   ""
    })
    sinon.assert.calledWith(setSubmittingStub, false)

    const { ui } = store.getState()

    assert.deepEqual(ui.userNotifications, {
      "forgot-password-sent": {
        type:  ALERT_TYPE_TEXT,
        props: {
          text: `If an account with the email "${email}" exists, an email has been sent with a password reset link.`
        }
      }
    })
  })
})
