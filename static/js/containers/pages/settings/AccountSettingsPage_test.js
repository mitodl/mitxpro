// @flow
import { assert } from "chai"
import sinon from "sinon"

import AccountSettingsPage, {
  AccountSettingsPage as InnerAccountSettingsPage
} from "./AccountSettingsPage"
import IntegrationTestHelper from "../../../util/integration_test_helper"
import { routes } from "../../../lib/urls"
import { ALERT_TYPE_TEXT } from "../../../constants"

describe("AccountSettingsPage", () => {
  const oldPassword = "password1"
  const newPassword = "password2"
  const confirmPassword = "password2"

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
        { oldPassword, newPassword },
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
})
