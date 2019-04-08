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

type LoginEmailFormProps = {
  onSubmit: Function
}

export const LoginEmailForm = ({ onSubmit }: LoginEmailFormProps) => (
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

const passwordValidation = yup.object().shape({
  password: yup
    .string()
    .required()
    .min(8)
})

type LoginPasswordFormProps = {
  onSubmit: Function
}

export const LoginPasswordForm = ({ onSubmit }: LoginPasswordFormProps) => (
  <Formik
    onSubmit={onSubmit}
    validationSchema={passwordValidation}
    initialValues={{ password: "" }}
    render={({ isSubmitting, isValid }) => (
      <Form>
        <label htmlFor="password">
          Password
          <Field type="password" name="password" />
        </label>
        <ErrorMessage name="password" component="div" />
        <button type="submit" disabled={isSubmitting || !isValid}>
          Login
        </button>
      </Form>
    )}
  />
)
