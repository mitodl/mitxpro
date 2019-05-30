// @flow
/* global SETTINGS:false */
import React from "react"

import { Formik, Field, Form, ErrorMessage } from "formik"

import { PasswordInput } from "./elements/inputs"
import FormError from "./elements/FormError"
import { changePasswordFormValidation } from "../../lib/validation"

type Props = {
  onSubmit: Function
}

export type ChangePasswordFormValues = {
  newPassword: string,
  confirmPassword: string
}

const ChangePasswordForm = ({ onSubmit }: Props) => (
  <Formik
    onSubmit={onSubmit}
    validationSchema={changePasswordFormValidation}
    initialValues={{
      newPassword:   "",
      reNewPassword: ""
    }}
    render={({ isSubmitting }) => (
      <Form>
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
