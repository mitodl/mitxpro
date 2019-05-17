// @flow
/* global SETTINGS:false */
import React from "react"
import * as yup from "yup"

import { Formik, Field, Form, ErrorMessage } from "formik"

import ScaledRecaptcha from "../ScaledRecaptcha"

const emailValidation = yup.object().shape({
  email: yup
    .string()
    .required()
    .email(),
  recaptcha: SETTINGS.recaptchaKey
    ? yup.string().required("Please verify you're not a robot")
    : yup.mixed().notRequired()
})

type Props = {
  onSubmit: Function
}

const RegisterEmailForm = ({ onSubmit }: Props) => (
  <Formik
    onSubmit={onSubmit}
    validationSchema={emailValidation}
    initialValues={{
      email:     "",
      recaptcha: SETTINGS.recaptchaKey ? "" : undefined
    }}
    render={({ isSubmitting, isValid, setFieldValue }) => (
      <Form>
        <label htmlFor="email">
          Email
          <Field type="email" name="email" />
        </label>
        <ErrorMessage name="email" component="div" />
        {SETTINGS.recaptchaKey ? (
          <React.Fragment>
            <ScaledRecaptcha
              onRecaptcha={value => setFieldValue("recaptcha", value)}
              recaptchaKey={SETTINGS.recaptchaKey}
            />
            <ErrorMessage name="recaptcha" component="div" />
          </React.Fragment>
        ) : null}
        <button type="submit" disabled={isSubmitting || !isValid}>
          Next
        </button>
      </Form>
    )}
  />
)

export default RegisterEmailForm
