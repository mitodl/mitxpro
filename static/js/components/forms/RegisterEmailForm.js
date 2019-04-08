// @flow
import React from "react"
import * as yup from "yup"

import { Formik, Field, Form, ErrorMessage } from "formik"

const emailValidation = yup.object().shape({
  email: yup
    .string()
    .required()
    .email()
})

type Props = {
  onSubmit: Function
}

const RegisterEmailForm = ({ onSubmit }: Props) => (
  <Formik
    onSubmit={onSubmit}
    validationSchema={emailValidation}
    initialValues={{ email: "" }}
    render={({ isSubmitting, isValid }) => (
      <Form>
        <label htmlFor="email">
          Email
          <Field type="email" name="email" />
        </label>
        <ErrorMessage name="email" component="div" />
        <button type="submit" disabled={isSubmitting || !isValid}>
          Next
        </button>
      </Form>
    )}
  />
)

export default RegisterEmailForm
