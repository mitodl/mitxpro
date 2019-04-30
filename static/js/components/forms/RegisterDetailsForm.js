// @flow
import React from "react"
import * as yup from "yup"
import {__, includes} from "ramda"

import { Formik, Field, Form, ErrorMessage, FieldArray } from "formik"

const US_ALPHA_2 = "US"
const CA_ALPHA_2 = "CA"

const US_POSTAL_CODE_REGEX = /[0-9]{5}(-[0-9]{4})/
const CA_POSTAL_CODE_REGEX = /[0-9][A-Z][0-9] [A-Z][0-9][A-Z]/

const detailsValidation = yup.object().shape({
  name:     yup.label("Name").string().required(),
  password: yup
    .label("Password")
    .string()
    .required()
    .min(8),
  legal_address: yup.object().shape({
    first_name: yup.label("First Name").string().required(),
    last_name: yup.label("Last Name").string().required(),
    city: yup.label("City").string().required(),
    street_address: yup.arrayOf(
      yup.string().max(60)
    ),
    state_or_territory: yup.mixed().label("State/Territory").when("country", {
      is: includes(__, [US_ALPHA_2, CA_ALPHA_2]),
      then: yup.string().required().matches(/[A-Z]{2}-[A-Z]{2,3}]/)
    }),
    country: yup.label("Country").string().length(2).required(),
    postal_code: yup.label("Zip/Postal Code").string().when("country", (country, schema) => {
      if (country == US_ALPHA_2) {
        return schema.required().matches(US_POSTAL_CODE_REGEX, {message: "Postal Code must be formatted as either 'NNNNN' or 'NNNNN-NNNN'"})
      } else if (country == CA_ALPHA_2) {
        return schema.required().matches(US_POSTAL_CODE_REGEX, {message: "Postal Code must be formatted as 'ANA NAN'"})
      }
    })
  })
})

type Props = {
  onSubmit: Function
}

const INITIAL_VALUES = {
  name: "",
  password: "",
  legal_address: {
    first_name: "",
    last_name: "",
    street_address: [
      ""
    ],
    city: "",
    country: "",
    state_or_territory: "",
    postal_code: ""
  }
}

const RegisterDetailsForm = ({ onSubmit }: Props) => (
  <Formik
    onSubmit={onSubmit}
    validationSchema={detailsValidation}
    initialValues={INITIAL_VALUES}
    render={({ isSubmitting, isValid, values }) => (
      <Form>
        <div>
          <label htmlFor="name">
            Legal Name
            <Field type="text" name="name" />
          </label>
          <ErrorMessage name="name" component="div" />
        </div>
        <div>
          <label htmlFor="legal_address.first_name">
            First Name
            <Field type="text" name="legal_address.first_name" />
          </label>
          <ErrorMessage name="legal_address.first_name" component="div" />
        </div>
        <div>
          <label htmlFor="legal_address.last_name">
            Last Name
            <Field type="text" name="legal_address.last_name" />
          </label>
          <ErrorMessage name="legal_address.last_name" component="div" />
        </div>
        <div>
          <label htmlFor="password">
            Password
            <Field type="password" name="password" />
          </label>
          <ErrorMessage name="password" component="div" />
        </div>
        <div>
          {/* LegalAddress fields */}
          <label>
            Address
            <FieldArray
              name="legal_address.treet_address"
              render={arrayHelpers => (
                <div>
                  {values.legal_address.street_address.map((line, index) => (
                    <div key={index}>
                      <Field name={`legal_address.street_address[${index}]`} />
                      {index != 0 ? <button type="button" onClick={() => arrayHelpers.remove(index)}>
                        -
                      </button> : null}
                    </div>
                  ))}
                  <button
                    type="button"
                    onClick={() => arrayHelpers.push("")}
                  >
                    +
                  </button>
                </div>
              )}
            />
          </label>
        </div>
        <button type="submit" disabled={isSubmitting || !isValid}>
          Register
        </button>
      </Form>
    )}
  />
)

export default RegisterDetailsForm
