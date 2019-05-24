// @flow
import { assert } from "chai"

import ViewProfilePage, {
  ViewProfilePage as InnerViewProfilePage
} from "./ViewProfilePage"
import { makeUser } from "../../../factories/user"
import IntegrationTestHelper from "../../../util/integration_test_helper"

describe("ViewProfilePage", () => {
  let helper, renderPage
  const user = makeUser()

  beforeEach(() => {
    helper = new IntegrationTestHelper()

    renderPage = helper.configureHOCRenderer(
      ViewProfilePage,
      InnerViewProfilePage,
      {
        entities: {
          currentUser: user
        }
      },
      {}
    )
  })

  afterEach(() => {
    helper.cleanup()
  })

  it("renders the page", async () => {
    const { inner } = await renderPage()
    assert.isTrue(inner.find(".submit-row").exists())
    // $FlowFixMe: user.legal_address is not null
    assert.isTrue(inner.text().includes(user.legal_address.street_address[0]))
    // $FlowFixMe: user.profile is not null
    assert.isTrue(inner.text().includes(user.profile.company))
  })
})
