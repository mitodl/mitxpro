// @flow
/* global SETTINGS:false */
import React from "react"

import { Formik, Field, Form, ErrorMessage } from "formik"

import { PasswordInput, EmailInput } from "./elements/inputs"
import FormError from "./elements/FormError"
import { changePasswordFormValidation } from "../../lib/validation"

import type { User } from "../../flow/authTypes"

type Props = {
  onSubmit: Function,
  user: User
}

export type ChangePasswordFormValues = {
  oldPassword: string,
  newPassword: string,
  confirmPassword: string,
  email: string
}

const ChangePasswordForm = ({ onSubmit, user }: Props) => (
  <Formik
    onSubmit={onSubmit}
    validationSchema={changePasswordFormValidation}
    initialValues={{
      email:           user.email,
      user_email:      user.email,
      oldPassword:     "",
      newPassword:     "",
      confirmPassword: ""
    }}
    validate={async values => {
      try {
        await changePasswordFormValidation.validate(values)
        return {}
      } catch (error) {
        const FIRST_ERROR = 0
        return error.inner.reduce((errors, error) => {
          return {
            ...errors,
            [error.path]: error.errors[FIRST_ERROR]
          }
        }, {})
      }
    }}
    render={({ isSubmitting }) => (
      <Form>
        <section className="email-section">
          <div className="form-group">
            <label htmlFor="email">Email</label>
            <Field
              name="email"
              className="form-control"
              component={EmailInput}
            />
            <ErrorMessage name="email" component={FormError} />
          </div>
          <div className="form-group hidden">
            <label htmlFor="user_email">User Email</label>
            <Field
              name="user_email"
              className="form-control"
              component={EmailInput}
              value={user.email}
            />
            <ErrorMessage name="user_email" component={FormError} />
          </div>
          <div className="light-gray-text">Name that will appear on emails</div>
        </section>

        <section className="password-section">
          <div className="form-group">
            <label htmlFor="oldPassword">Old Password</label>
            <Field
              name="oldPassword"
              className="form-control"
              component={PasswordInput}
            />
            <ErrorMessage name="oldPassword" component={FormError} />
          </div>
          <div className="form-group">
            <label htmlFor="newPassword">New Password</label>
            <Field
              name="newPassword"
              className="form-control"
              component={PasswordInput}
            />
            <ErrorMessage name="newPassword" component={FormError} />
          </div>
          <div className="form-group">
            <label htmlFor="confirmPassword">Confirm Password</label>
            <Field
              name="confirmPassword"
              className="form-control"
              component={PasswordInput}
            />
            <ErrorMessage name="confirmPassword" component={FormError} />
          </div>
        </section>
        <div className="row submit-row no-gutters justify-content-end">
          <button
            type="submit"
            className="btn btn-primary btn-light-blue"
            disabled={isSubmitting}
          >
            Submit
          </button>
        </div>
      </Form>
    )}
  />
)

export default ChangePasswordForm
