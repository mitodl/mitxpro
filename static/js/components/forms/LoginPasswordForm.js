// @flow
import React from "react"
import * as yup from "yup"

import { Formik, Field, Form, ErrorMessage } from "formik"

import FormError from "./elements/FormError"
import { PasswordInput } from "./elements/inputs"
import { passwordValidationShape } from "../../lib/form"

const passwordValidation = yup.object().shape({
  password: passwordValidationShape
})

type LoginPasswordFormProps = {
  onSubmit: Function
}

const LoginPasswordForm = ({ onSubmit }: LoginPasswordFormProps) => (
  <Formik
    onSubmit={onSubmit}
    validationSchema={passwordValidation}
    initialValues={{ password: "" }}
    render={({ isSubmitting }) => (
      <Form>
        <div className="form-group">
          <label htmlFor="password">Password</label>
          <Field
            name="password"
            className="form-control"
            component={PasswordInput}
          />
          <ErrorMessage name="password" component={FormError} />
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

export default LoginPasswordForm
