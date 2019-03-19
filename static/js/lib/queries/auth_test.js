// @flow
import { assert } from "chai"

import { authSelector } from "./auth"

describe("auth reducers", () => {
  describe("authSelector", () => {
    it("should return the auth state", () => {
      const auth = {
        key: "value"
      }
      assert.equal(authSelector({ entities: { auth } }), auth)
    })
  })
})
