// @flow
import { assert } from "chai"

import IntegrationTestHelper from "../../../util/integration_test_helper"
import RegisterConfirmPage, {
  RegisterConfirmPage as InnerRegisterConfirmPage
} from "./RegisterConfirmPage"
import { STATE_REGISTER_DETAILS } from "../../../lib/auth"

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
})
