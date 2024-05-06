// @flow
import { assert } from "chai";
import { ValidationError } from "yup";

import {
  changeEmailFormValidation,
  changePasswordFormValidation,
  resetPasswordFormValidation,
} from "./validation";

describe("validation utils", () => {
  describe("resetPasswordFormValidation", () => {
    it(`should validate with matching passwords`, async () => {
      const inputs = {
        newPassword: "password1",
        confirmPassword: "password1",
      };
      const result = await resetPasswordFormValidation.validate(inputs);

      assert.deepEqual(result, inputs);
    });

    //
    [
      [
        { newPassword: "", confirmPassword: "" },
        ["Confirm Password is a required field"],
      ],
      [
        { newPassword: "password1", confirmPassword: "password2" },
        ["Passwords must match"],
      ],
    ].forEach(([inputs, errors]) => {
      it(`should throw an error with inputs=${JSON.stringify(
        inputs,
      )}`, async () => {
        const promise = resetPasswordFormValidation.validate(inputs);

        const result = await assert.isRejected(promise, ValidationError);

        assert.deepEqual(result.errors, errors);
      });
    });
  });

  describe("ChangePasswordFormValidation", () => {
    it(`should validate with matching passwords`, async () => {
      const inputs = {
        oldPassword: "old-password",
        newPassword: "password1",
        confirmPassword: "password1",
      };
      const result = await changePasswordFormValidation.validate(inputs);

      assert.deepEqual(result, inputs);
    });

    //
    [
      [
        {
          oldPassword: "",
          newPassword: "password1",
          confirmPassword: "password1",
        },
        ["Old Password is a required field"],
      ],
      [
        {
          oldPassword: "password1",
          newPassword: "",
          confirmPassword: "",
        },
        ["Confirm Password is a required field"],
      ],
      [
        {
          oldPassword: "password1",
          newPassword: "password1",
          confirmPassword: "password2",
        },
        ["Passwords must match"],
      ],
      [
        {
          oldPassword: "password1",
          newPassword: "pass",
          confirmPassword: "pass",
        },
        ["New Password must be at least 8 characters"],
      ],
      [
        {
          oldPassword: "password1",
          newPassword: "password",
          confirmPassword: "password",
        },
        ["Password must contain at least one letter and number"],
      ],
    ].forEach(([inputs, errors]) => {
      it(`should throw an error with inputs=${JSON.stringify(
        inputs,
      )}`, async () => {
        const promise = changePasswordFormValidation.validate(inputs);

        const result = await assert.isRejected(promise, ValidationError);

        assert.deepEqual(result.errors, errors);
      });
    });
  }),
    describe("ChangeEmailFormValidation", () => {
      it(`should validate with different email`, async () => {
        const inputs = {
          email: "test@example.com",
          confirmPassword: "password1",
        };
        const result = await changeEmailFormValidation.validate(inputs, {
          context: { currentEmail: "abc@example.com" },
        });

        assert.deepEqual(result, inputs);
      });

      //
      [
        [
          {
            email: "abc@example.com",
            confirmPassword: "password",
          },
          ["Email cannot be same, Use a different one"],
        ],
        [
          {
            email: "test@example.com",
            confirmPassword: "",
          },
          ["Confirm Password is a required field"],
        ],
        [
          {
            email: "test@example.com",
            confirmPassword: "abcd",
          },
          ["Confirm Password must be at least 8 characters"],
        ],
      ].forEach(([inputs, errors]) => {
        it(`should throw an error with inputs=${JSON.stringify(
          inputs,
        )}`, async () => {
          const promise = changeEmailFormValidation.validate(inputs, {
            context: { currentEmail: "abc@example.com" },
          });

          const result = await assert.isRejected(promise, ValidationError);

          assert.deepEqual(result.errors, errors);
        });
      });
    });
});
