// @flow
import { assert } from "chai"
import { ValidationError } from "yup"

import { changePasswordFormValidation } from "./validation"

describe("validation utils", () => {
  describe("changePasswordFormValidation", () => {
    it(`should validate with matching passwords`, async () => {
      const inputs = {
        newPassword:     "password1",
        confirmPassword: "password1"
      }
      const result = await changePasswordFormValidation.validate(inputs)

      assert.deepEqual(result, inputs)
    })

    //
    ;[
      [
        { newPassword: "", confirmPassword: "" },
        ["Confirm Password is a required field"]
      ],
      [
        { newPassword: "password1", confirmPassword: "password2" },
        ["Passwords must match"]
      ]
    ].forEach(([inputs, errors]) => {
      it(`should throw an error with inputs=${JSON.stringify(
        inputs
      )}`, async () => {
        const promise = changePasswordFormValidation.validate(inputs)

        const result = await assert.isRejected(promise, ValidationError)

        assert.deepEqual(result.errors, errors)
      })
    })
  })
})
