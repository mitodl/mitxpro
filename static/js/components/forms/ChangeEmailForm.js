// @flow
/* global SETTINGS:false */
import React from "react"

import {
  Formik,
  Field,
  Form,
  ErrorMessage,
  yupToFormErrors,
  validateYupSchema
} from "formik"

import { PasswordInput, EmailInput } from "./elements/inputs"
import FormError from "./elements/FormError"
import { changeEmailFormValidation } from "../../lib/validation"

import type { User } from "../../flow/authTypes"

type Props = {
  onSubmit: Function,
  user: User
}

export type ChangeEmailFormValues = {
  email: string,
  confirmPassword: string
}

const ChangeEmailForm = ({ onSubmit, user }: Props) => (
  <Formik
    onSubmit={onSubmit}
    initialValues={{
      email:           user.email,
      confirmPassword: ""
    }}
    validate={values =>
      validateYupSchema(values, changeEmailFormValidation, false, {
        currentEmail: user.email
      }).catch(err => Promise.reject(yupToFormErrors(err)))
    }
    render={({ isSubmitting }) => (
      <Form>
        <section className="email-section">
          <h4>Change Email</h4>
          <div className="form-group">
            <label htmlFor="email">Email</label>
            <Field
              name="email"
              className="form-control"
              component={EmailInput}
            />
            <ErrorMessage name="email" component={FormError} />
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
          <div className="light-gray-text">
            Password required to change email address
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

export default ChangeEmailForm
