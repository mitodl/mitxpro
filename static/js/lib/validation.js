// @flow
import * as yup from "yup"

// Field validations

export const emailFieldValidation = yup
  .string()
  .label("Email")
  .required()
  .email("Invalid email")

export const passwordFieldValidation = yup
  .string()
  .label("Password")
  .required()
  .min(8)

export const newPasswordFieldValidation = passwordFieldValidation.matches(
  /^(?=.*[0-9])(?=.*[a-zA-Z]).*$/,
  {
    message: "Password must contain at least one letter and number"
  }
)

export const resetPasswordFormValidation = yup.object().shape({
  newPassword:     newPasswordFieldValidation.label("New Password"),
  confirmPassword: yup
    .string()
    .label("Confirm Password")
    .required()
    .oneOf([yup.ref("newPassword")], "Passwords must match")
})

export const changePasswordFormValidation = yup.object().shape({
  email: emailFieldValidation.label("Email"),

  user_email: yup.string().label("User Email"),

  /* eslint-disable camelcase */
  oldPassword: yup
    .string()
    .label("Old Password")
    .when(["email", "user_email"], (email, user_email, schema) =>
      user_email === email ? schema.required() : schema.notRequired()
    ),

  newPassword: yup
    .string()
    .label("New Password")
    .when(["email", "user_email"], (email, user_email, schema) =>
      user_email === email
        ? schema
          .matches(/^(?=.*[0-9])(?=.*[a-zA-Z]).*$/, {
            message: "Password must contain at least one letter and number"
          })
          .required()
          .min(8)
        : schema.matches(/^.*$/).notRequired()
    ),

  confirmPassword: yup
    .string()
    .label("Confirm Password")
    .when(["email", "user_email"], (email, user_email, schema) =>
      user_email === email ? schema.required().min(8) : schema.notRequired()
    )
    .oneOf([yup.ref("newPassword")], "Passwords must match")
})
