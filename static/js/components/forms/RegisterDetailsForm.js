// @flow
import React from "react"
import * as yup from "yup"

import { Formik, Field, Form, ErrorMessage } from "formik"

const detailsValidation = yup.object().shape({
  name:     yup.string().required(),
  password: yup
    .string()
    .required()
    .min(8)
})

type Props = {
  onSubmit: Function
}

const RegisterDetailsForm = ({ onSubmit }: Props) => (
  <Formik
    onSubmit={onSubmit}
    validationSchema={detailsValidation}
    initialValues={{ name: "", password: "" }}
    render={({ isSubmitting, isValid }) => (
      <Form>
        <label htmlFor="name">
          Name
          <Field type="text" name="name" />
        </label>
        <ErrorMessage name="name" component="div" />
        <label htmlFor="password">
          Password
          <Field type="password" name="password" />
        </label>
        <ErrorMessage name="password" component="div" />
        <button type="submit" disabled={isSubmitting || !isValid}>
          Register
        </button>
      </Form>
    )}
  />
)

export default RegisterDetailsForm
