// @flow
import { assert } from "chai"

import IntegrationTestHelper from "../../../util/integration_test_helper"
import RegisterConfirmPage, {
  RegisterConfirmPage as InnerRegisterConfirmPage
} from "./RegisterConfirmPage"
import {
  STATE_REGISTER_DETAILS,
  STATE_INVALID_LINK,
  STATE_EXISTING_ACCOUNT,
  STATE_INVALID_EMAIL
} from "../../../lib/auth"
import { routes } from "../../../lib/urls"

describe("RegisterConfirmPage", () => {
  let helper, renderPage

  beforeEach(() => {
    helper = new IntegrationTestHelper()
    renderPage = helper.configureHOCRenderer(
      RegisterConfirmPage,
      InnerRegisterConfirmPage,
      {},
      {
        location: {
          search: ""
        }
      }
    )
  })

  afterEach(() => {
    helper.cleanup()
  })

  it("shows a message when the confirmation page is displayed and redirects", async () => {
    helper.handleRequestStub.returns({})
    const token = "asdf"
    const { inner, store } = await renderPage({
      entities: {
        auth: {
          state:         STATE_REGISTER_DETAILS,
          partial_token: token,
          extra_data:    {
            name: "name"
          }
        }
      }
    })

    inner.instance().componentDidUpdate({}, {})
    assert.deepEqual(store.getState().ui.userNotifications, {
      "email-verified": {
        type:  "text",
        props: {
          text:
            "Success! We've verified your email. Please finish your account creation below."
        }
      }
    })
    assert.equal(helper.currentLocation.pathname, "/create-account/details/")
    assert.equal(helper.currentLocation.search, `?partial_token=${token}`)
  })

  it("Shows a register link with invalid/expired confirmation code", async () => {
    helper.handleRequestStub.returns({})
    const token = "asdf"
    const { inner, store } = await renderPage({
      entities: {
        auth: {
          state:         STATE_INVALID_LINK,
          partial_token: token,
          extra_data:    {}
        }
      }
    })
    const confirmationErrorText = inner.find(".confirmation-message")
    assert.isNotNull(confirmationErrorText)
    assert.equal(
      confirmationErrorText.text().replace("<Link />", ""),
      "This invitation is invalid or has expired. Please ."
    )
  })

  it("Shows a login link with existing account message", async () => {
    helper.handleRequestStub.returns({})
    const token = "asdf"
    const { inner, store } = await renderPage({
      entities: {
        auth: {
          state:         STATE_EXISTING_ACCOUNT,
          partial_token: token,
          extra_data:    {}
        }
      }
    })
    const confirmationErrorText = inner.find(".confirmation-message")
    assert.isNotNull(confirmationErrorText)
    assert.equal(
      confirmationErrorText.text().replace("<Link />", ""),
      "You already have an xPRO account. Please ."
    )
  })

  it("Shows a register link with invalid or no confirmation code", async () => {
    helper.handleRequestStub.returns({})
    const token = "asdf"
    const { inner, store } = await renderPage({
      entities: {
        auth: {
          state:         STATE_INVALID_EMAIL,
          partial_token: token,
          extra_data:    {}
        }
      }
    })
    const confirmationErrorText = inner.find(".confirmation-message")
    assert.equal(
      confirmationErrorText.text().replace("<Link />", ""),
      "No confirmation code was provided or it has expired. ."
    )
  })
})
