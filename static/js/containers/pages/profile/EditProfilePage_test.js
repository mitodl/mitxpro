// @flow
import { assert } from "chai"

import EditProfilePage, {
  EditProfilePage as InnerEditProfilePage
} from "./EditProfilePage"
import {
  makeAnonymousUser,
  makeCountries,
  makeUser
} from "../../../factories/user"
import IntegrationTestHelper from "../../../util/integration_test_helper"

describe("EditProfilePage", () => {
  let helper, renderPage
  const user = makeUser()
  const countries = makeCountries()

  beforeEach(() => {
    helper = new IntegrationTestHelper()

    renderPage = helper.configureHOCRenderer(
      EditProfilePage,
      InnerEditProfilePage,
      {
        entities: {
          currentUser: user,
          countries:   countries
        }
      },
      {}
    )
  })

  afterEach(() => {
    helper.cleanup()
  })

  it("renders the page for a logged in user", async () => {
    const { inner } = await renderPage()
    assert.isTrue(inner.find("EditProfileForm").exists())
  })

  it("renders the page for an anonymous user", async () => {
    const { inner } = await renderPage({
      entities: {
        currentUser: makeAnonymousUser(),
        countries:   countries
      }
    })
    assert.isFalse(inner.find("EditProfileForm").exists())
    assert.isTrue(
      inner.text().includes("You must be logged in to edit your profile.")
    )
  })
})
