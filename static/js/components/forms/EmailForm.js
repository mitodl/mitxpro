// @flow
import React from "react"
import * as yup from "yup"

import { Formik, Field, Form, ErrorMessage } from "formik"

import FormError from "./elements/FormError"
import { EmailInput } from "./elements/inputs"
import { emailFieldValidation } from "../../lib/validation"

const emailValidation = yup.object().shape({
  email: emailFieldValidation
})

type EmailFormProps = {
  onSubmit: Function,
  children?: React$Element<*>
}

export type EmailFormValues = {
  email: string
}

const EmailForm = ({ onSubmit, children }: EmailFormProps) => (
  <Formik
    onSubmit={onSubmit}
    validationSchema={emailValidation}
    initialValues={{ email: "" }}
    render={({ isSubmitting }) => (
      <Form>
        <div className="form-group">
          <label htmlFor="email">Email</label>
          <Field
            name="email"
            className="form-control"
            component={EmailInput}
            autoComplete="email"
          />
          <ErrorMessage name="email" component={FormError} />
        </div>
        {children && <div className="form-group">{children}</div>}
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

export default EmailForm
