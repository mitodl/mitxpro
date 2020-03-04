// @flow
import { assert } from "chai"
import sinon from "sinon"

import AccountSettingsPage, {
  AccountSettingsPage as InnerAccountSettingsPage
} from "./AccountSettingsPage"
import IntegrationTestHelper from "../../../util/integration_test_helper"
import { routes } from "../../../lib/urls"
import { ALERT_TYPE_TEXT } from "../../../constants"
import { makeUser } from "../../../factories/user"

describe("AccountSettingsPage", () => {
  const oldPassword = "password1"
  const newPassword = "password2"
  const user = makeUser()
  const email = "abc@example.com"
  const confirmPassword = newPassword

  let helper, renderPage, setSubmittingStub

  beforeEach(() => {
    helper = new IntegrationTestHelper()

    setSubmittingStub = helper.sandbox.stub()

    renderPage = helper.configureHOCRenderer(
      AccountSettingsPage,
      InnerAccountSettingsPage,
      {},
      {}
    )
  })

  afterEach(() => {
    helper.cleanup()
  })

  it("displays a form", async () => {
    const { inner } = await renderPage()

    assert.ok(inner.find("ChangePasswordForm").exists())
  })

  //
  ;[
    [
      200,
      routes.accountSettings,
      "success",
      "Your password has been updated successfully."
    ],

    [
      400,
      routes.accountSettings,
      "danger",
      "Unable to reset your password, please try again later."
    ]
  ].forEach(([status, expectedUrl, expectedColor, expectedMessage]) => {
    it(`handles onSubmit with status=${status}`, async () => {
      const { inner, store } = await renderPage()

      helper.handleRequestStub.returns({
        status
      })

      const onSubmit = inner.find("ChangePasswordForm").prop("onSubmit")

      const resetFormStub = helper.sandbox.stub()

      await onSubmit(
        { oldPassword, newPassword, confirmPassword },
        { setSubmitting: setSubmittingStub, resetForm: resetFormStub }
      )
      sinon.assert.calledWith(
        helper.handleRequestStub,
        "/api/set_password/",
        "POST",
        {
          body: {
            current_password: oldPassword,
            new_password:     newPassword
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
      sinon.assert.calledWith(resetFormStub)

      const { ui } = store.getState()
      assert.deepEqual(ui.userNotifications, {
        "password-change": {
          type:  ALERT_TYPE_TEXT,
          color: expectedColor,
          props: {
            text: expectedMessage
          }
        }
      })
    })
  })

  //
  ;[
    [
      200,
      routes.accountSettings,
      "success",
      "You have been sent a verification email on your updated address. Please click on the link in the email to finish email address update."
    ],

    [
      400,
      routes.accountSettings,
      "danger",
      "Unable to update your email address, please try again later."
    ]
  ].forEach(([status, expectedUrl, expectedColor, expectedMessage]) => {
    it(`handles onSubmit with status=${status}`, async () => {
      const { inner, store } = await renderPage({
        entities: {
          currentUser: user
        }
      })

      helper.handleRequestStub.returns({
        status
      })

      const onSubmit = inner.find("ChangeEmailForm").prop("onSubmit")

      const resetFormStub = helper.sandbox.stub()

      await onSubmit(
        { email, oldPassword, newPassword, user },
        { setSubmitting: setSubmittingStub, resetForm: resetFormStub }
      )
      sinon.assert.calledWith(
        helper.handleRequestStub,
        "/api/change-emails/",
        "POST",
        {
          body: {
            new_email: email,
            password:  undefined
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
      sinon.assert.calledWith(resetFormStub)

      const { ui } = store.getState()
      assert.deepEqual(ui.userNotifications, {
        "email-change": {
          type:  ALERT_TYPE_TEXT,
          color: expectedColor,
          props: {
            text: expectedMessage
          }
        }
      })
    })
  })
})
