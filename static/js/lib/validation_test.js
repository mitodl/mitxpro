// @flow
import { assert } from "chai"
import { ValidationError } from "yup"

import {
  changePasswordFormValidation,
  resetPasswordFormValidation
} from "./validation"

describe("validation utils", () => {
  describe("resetPasswordFormValidation", () => {
    it(`should validate with matching passwords`, async () => {
      const inputs = {
        newPassword:     "password1",
        confirmPassword: "password1"
      }
      const result = await resetPasswordFormValidation.validate(inputs)

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
        const promise = resetPasswordFormValidation.validate(inputs)

        const result = await assert.isRejected(promise, ValidationError)

        assert.deepEqual(result.errors, errors)
      })
    })
  })

  describe("ChangePasswordFormValidation", () => {
    it(`should validate with matching passwords`, async () => {
      const inputs = {
        email:           "abc@example.com",
        oldPassword:     "old-password",
        newPassword:     "password1",
        confirmPassword: "password1"
      }
      const result = await changePasswordFormValidation.validate(inputs)

      assert.deepEqual(result, inputs)
    })

    //
    ;[
      [
        {
          email:           "abc@example.com",
          user_email:      "abc@example.com",
          oldPassword:     "",
          newPassword:     "password1",
          confirmPassword: "password1"
        },
        ["Old Password is a required field"]
      ],
      [
        {
          email:           "abc@example.com",
          user_email:      "abc@example.com",
          oldPassword:     "password1",
          newPassword:     "",
          confirmPassword: ""
        },
        ["Confirm Password is a required field"]
      ],
      [
        {
          email:           "abc@example.com",
          oldPassword:     "password1",
          newPassword:     "password1",
          confirmPassword: "password2"
        },
        ["Passwords must match"]
      ],
      [
        {
          email:           "abc@example.com",
          user_email:      "abc@example.com",
          oldPassword:     "password1",
          newPassword:     "pass",
          confirmPassword: "pass"
        },
        ["Confirm Password must be at least 8 characters"]
      ],
      [
        {
          email:           "abc@example.com",
          user_email:      "abc@example.com",
          oldPassword:     "password1",
          newPassword:     "password",
          confirmPassword: "password"
        },
        ["Password must contain at least one letter and number"]
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
