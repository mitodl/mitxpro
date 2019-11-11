// @flow
import { assert } from "chai"
import sinon from "sinon"

import LoginForgotPasswordConfirmPage, {
  LoginForgotPasswordConfirmPage as InnerLoginForgotPasswordConfirmPage
} from "./LoginForgotPasswordConfirmPage"
import IntegrationTestHelper from "../../../util/integration_test_helper"
import { routes } from "../../../lib/urls"
import { ALERT_TYPE_TEXT } from "../../../constants"

describe("LoginForgotPasswordConfirmPage", () => {
  const newPassword = "pass1"
  const confirmPassword = "pass2"
  const token = "token1"
  const uid = "uid1"
  let helper, renderPage, setSubmittingStub

  beforeEach(() => {
    helper = new IntegrationTestHelper()

    setSubmittingStub = helper.sandbox.stub()

    renderPage = helper.configureHOCRenderer(
      LoginForgotPasswordConfirmPage,
      InnerLoginForgotPasswordConfirmPage,
      {},
      {
        match: {
          params: { token, uid }
        }
      }
    )
  })

  afterEach(() => {
    helper.cleanup()
  })

  it("displays a form", async () => {
    const { inner } = await renderPage()

    assert.ok(inner.find("ResetPasswordForm").exists())
  })

  //
  ;[
    [
      200,
      routes.login.begin,
      "Your password has been updated, you may use it to sign in now."
    ],

    [
      400,
      routes.login.forgot.begin,
      "Unable to reset your password with that link, please try again."
    ]
  ].forEach(([status, expectedUrl, expectedMessage]) => {
    it(`handles onSubmit with status=${status}`, async () => {
      const { inner, store } = await renderPage()

      helper.handleRequestStub.returns({
        status
      })

      const onSubmit = inner.find("ResetPasswordForm").prop("onSubmit")

      await onSubmit(
        { newPassword, confirmPassword },
        { setSubmitting: setSubmittingStub }
      )
      sinon.assert.calledWith(
        helper.handleRequestStub,
        "/api/password_reset/confirm/",
        "POST",
        {
          body: {
            new_password:    newPassword,
            re_new_password: confirmPassword,
            token,
            uid
          },
          credentials: undefined,
          headers:     { "X-CSRFTOKEN": null }
        }
      )

      assert.lengthOf(helper.browserHistory, 2)
      assert.include(helper.browserHistory.location, {
        pathname: expectedUrl,
        search:   ""
      })
      sinon.assert.calledWith(setSubmittingStub, false)

      const { ui } = store.getState()
      assert.deepEqual(ui.userNotifications, {
        "forgot-password-confirm": {
          type:  ALERT_TYPE_TEXT,
          props: {
            text: expectedMessage
          }
        }
      })
    })
  })
})
