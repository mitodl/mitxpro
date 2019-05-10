// @flow
import { assert } from "chai"

import enrollment from "./enrollment"

describe("enrollment reducers", () => {
  describe("enrollmentsSelector", () => {
    it("should return the enrollments state", () => {
      const enrollments = {
        key: "value"
      }
      assert.equal(
        enrollment.enrollmentsSelector({ entities: { enrollments } }),
        enrollments
      )
    })
  })
})
