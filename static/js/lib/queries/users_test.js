// @flow
import { assert } from "chai"

import { currentUserSelector } from "./users"

describe("users reducers", () => {
  describe("currentUserSelector", () => {
    it("should return the user context", () => {
      const currentUser = {
        key: "value"
      }
      assert.equal(
        currentUserSelector({ entities: { currentUser } }),
        currentUser
      )
    })
  })
})
