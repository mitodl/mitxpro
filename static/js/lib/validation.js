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
  emailPassword: yup
    .string()
    .label("Confirm Password")
    .when(["email", "$currentEmail"], (email, currentEmail, schema) =>
      currentEmail !== email ? schema.required().min(8) : schema.notRequired()
    ),

  oldPassword: yup
    .string()
    .label("Old Password")
    .when(["email", "$currentEmail"], (email, currentEmail, schema) =>
      currentEmail === email ? schema.required() : schema.notRequired()
    ),

  newPassword: newPasswordFieldValidation
    .label("New Password")
    .when(["email", "$currentEmail"], (email, currentEmail, schema) =>
      currentEmail === email ? schema.required() : schema.notRequired()
    ),

  confirmPassword: yup
    .string()
    .label("Confirm Password")
    .when(["email", "$currentEmail"], (email, currentEmail, schema) =>
      currentEmail === email ? schema.required().min(8) : schema.notRequired()
    )
    .oneOf([yup.ref("newPassword")], "Passwords must match")
})
