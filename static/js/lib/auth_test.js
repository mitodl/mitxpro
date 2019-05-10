// @flow
import { assert } from "chai"

import { generateLoginRedirectUrl } from "./auth"
import { routes } from "../lib/urls"

describe("auth lib function", () => {
  it("generateLoginRedirectUrl should generate a url to redirect to after login", () => {
    window.location = "/protected/route?var=abc"
    const redirectUrl = generateLoginRedirectUrl()
    assert.equal(
      redirectUrl,
      `${routes.login.begin}?next=%2Fprotected%2Froute%3Fvar%3Dabc`
    )
  })
})
