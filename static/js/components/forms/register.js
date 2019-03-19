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

type RegisterEmailFormProps = {
  onSubmit: Function
}

export const RegisterEmailForm = ({ onSubmit }: RegisterEmailFormProps) => (
  <Formik
    onSubmit={onSubmit}
    validationSchema={emailValidation}
    initialValues={{ email: "" }}
    render={({ isSubmitting }) => (
      <Form>
        <label htmlFor="email">
          Email
          <Field type="email" name="email" />
        </label>
        <ErrorMessage name="email" component="div" />
        <button type="submit" disabled={isSubmitting}>
          Next
        </button>
      </Form>
    )}
  />
)

const profileValidation = yup.object().shape({
  name:     yup.string().required(),
  password: yup.string().required()
})

type RegisterProfileFormProps = {
  onSubmit: Function
}

export const RegisterProfileForm = ({ onSubmit }: RegisterProfileFormProps) => (
  <Formik
    onSubmit={onSubmit}
    validationSchema={profileValidation}
    initialValues={{ name: "", password: "" }}
    render={({ isSubmitting }) => (
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
        <button type="submit" disabled={isSubmitting}>
          Register
        </button>
      </Form>
    )}
  />
)
