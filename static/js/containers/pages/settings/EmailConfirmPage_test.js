// @flow
import { assert } from "chai"

import IntegrationTestHelper from "../../../util/integration_test_helper"
import EmailConfirmPage, {
  EmailConfirmPage as InnerEmailConfirmPage
} from "./EmailConfirmPage"
import { STATE_REGISTER_DETAILS } from "../../../lib/auth"

describe("EmailConfirmPage", () => {
  let helper, renderPage

  beforeEach(() => {
    helper = new IntegrationTestHelper()
    renderPage = helper.configureHOCRenderer(
      EmailConfirmPage,
      InnerEmailConfirmPage,
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

  it("shows a message when the confirmation page is displayed", async () => {
    helper.handleRequestStub.returns({})
    const token = "asdf"
    const { inner, store } = await renderPage({
      entities: {
        updateEmail: {
          confirmed: true
        }
      }
    })

    inner.instance().componentDidUpdate({}, {})
    assert.deepEqual(store.getState().ui.userNotifications, {
      "email-verified": {
        type:  "text",
        props: {
          text:
            "Success! We've verified your email. You email has been updated."
        }
      }
    })
  })

  it("shows a message when the error page is displayed", async () => {
    helper.handleRequestStub.returns({})
    const token = "asdf"
    const { inner, store } = await renderPage({
      entities: {
        updateEmail: {
          confirmed: false
        }
      }
    })

    inner.instance().componentDidUpdate({}, {})
    assert.deepEqual(store.getState().ui.userNotifications, {
      "email-verified": {
        type:  "text",
        color: "danger",
        props: {
          text: "Error! No confirmation code was provided or it has expired."
        }
      }
    })
  })
})
