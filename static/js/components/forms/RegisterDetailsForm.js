// @flow
import React from "react"
import * as yup from "yup"
import { __, includes, find, propEq } from "ramda"

import { Formik, Field, Form, ErrorMessage, FieldArray } from "formik"
import type { Country } from "../../flow/authTypes"

const US_ALPHA_2 = "US"
const CA_ALPHA_2 = "CA"

const US_POSTAL_CODE_REGEX = /[0-9]{5}(-[0-9]{4}){0,1}/
const CA_POSTAL_CODE_REGEX = /[0-9][A-Z][0-9] [A-Z][0-9][A-Z]/

const detailsValidation = yup.object().shape({
  name: yup
    .string()
    .label("Name")
    .required(),
  password: yup
    .string()
    .label("Password")
    .required()
    .min(8),
  legal_address: yup.object().shape({
    first_name: yup
      .string()
      .label("First Name")
      .required(),
    last_name: yup
      .string()
      .label("Last Name")
      .required(),
    city: yup
      .string()
      .label("City")
      .required(),
    street_address: yup
      .array()
      .of(yup.string().max(60))
      .min(1)
      .max(5),
    state_or_territory: yup
      .mixed()
      .label("State/Territory")
      .when("country", {
        is:   includes(__, [US_ALPHA_2, CA_ALPHA_2]),
        then: yup
          .string()
          .required()
          .matches(/[A-Z]{2}-[A-Z]{2,3}/)
      }),
    country: yup
      .string()
      .label("Country")
      .length(2)
      .required(),
    postal_code: yup
      .string()
      .label("Zip/Postal Code")
      .when("country", (country, schema) => {
        if (country === US_ALPHA_2) {
          return schema
            .required()
            .matches(US_POSTAL_CODE_REGEX, {
              message:
                "Postal Code must be formatted as either 'NNNNN' or 'NNNNN-NNNN'"
            })
        } else if (country === CA_ALPHA_2) {
          return schema
            .required()
            .matches(CA_POSTAL_CODE_REGEX, {
              message: "Postal Code must be formatted as 'ANA NAN'"
            })
        }
      })
  })
})

type Props = {
  onSubmit: Function,
  countries: Array<Country>
}

const INITIAL_VALUES = {
  name:          "",
  password:      "",
  legal_address: {
    first_name:         "",
    last_name:          "",
    street_address:     [""],
    city:               "",
    country:            "",
    state_or_territory: "",
    postal_code:        ""
  }
}

const RegisterDetailsForm = ({ onSubmit, countries }: Props) => (
  <Formik
    onSubmit={onSubmit}
    validationSchema={detailsValidation}
    initialValues={INITIAL_VALUES}
    render={({
      isSubmitting,
      setFieldValue,
      setFieldTouched,
      isValid,
      values
    }) => (
      <Form>
        <div>
          <label htmlFor="name">
            Legal Name*
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
            Last Name*
            <Field type="text" name="legal_address.last_name" />
          </label>
          <ErrorMessage name="legal_address.last_name" component="div" />
        </div>
        <div>
          <label htmlFor="password">
            Password*
            <Field type="password" name="password" />
          </label>
          <ErrorMessage name="password" component="div" />
        </div>
        <div>
          {/* LegalAddress fields */}
          <label>
            Street Address*
            <FieldArray
              name="legal_address.street_address"
              render={arrayHelpers => (
                <div>
                  {values.legal_address.street_address.map((line, index) => (
                    <div key={index}>
                      <Field name={`legal_address.street_address[${index}]`} />
                      {index !== 0 ? (
                        <button
                          type="button"
                          onClick={() => arrayHelpers.remove(index)}
                        >
                          -
                        </button>
                      ) : null}
                    </div>
                  ))}
                  {values.legal_address.street_address.length < 5 ? (
                    <button type="button" onClick={() => arrayHelpers.push("")}>
                      +
                    </button>
                  ) : null}
                </div>
              )}
            />
          </label>
        </div>
        <div>
          <label>
            Country*
            <Field
              component="select"
              name="legal_address.country"
              onChange={e => {
                setFieldValue("legal_address.country", e.target.value)
                setFieldTouched("legal_address.country")
                setFieldValue("legal_address.state_or_territory", "")
              }}
            >
              <option value="">-----</option>
              {countries
                ? countries.map((country, i) => (
                  <option key={i} value={country.code}>
                    {country.name}
                  </option>
                ))
                : null}
            </Field>
          </label>
          <ErrorMessage name="legal_address.country" component="div" />
        </div>
        {includes(values.legal_address.country, [US_ALPHA_2, CA_ALPHA_2]) ? (
          <div>
            <label>
              State/Province*
              <Field component="select" name="legal_address.state_or_territory">
                <option value="">-----</option>
                {find(
                  propEq("code", values.legal_address.country),
                  countries
                ).states.map((state, i) => (
                  <option key={i} value={state.code}>
                    {state.name}
                  </option>
                ))}
              </Field>
            </label>
            <ErrorMessage
              name="legal_address.state_or_territory"
              component="div"
            />
          </div>
        ) : (
          <Field
            type="hidden"
            name="legal_address.state_or_territory"
            value=""
          />
        )}
        <div>
          <label htmlFor="legal_address.city">
            City*
            <Field type="text" name="legal_address.city" />
          </label>
          <ErrorMessage name="legal_address.city" component="div" />
        </div>
        {includes(values.legal_address.country, [US_ALPHA_2, CA_ALPHA_2]) ? (
          <div>
            <label htmlFor="legal_address.postal_code">
              Zip/Postal Code*
              <Field type="text" name="legal_address.postal_code" />
            </label>
            <ErrorMessage name="legal_address.postal_code" component="div" />
          </div>
        ) : (
          <Field type="hidden" name="legal_address.postal_code" value="" />
        )}
        <button type="submit" disabled={isSubmitting || !isValid}>
          {`${isValid}`}
        </button>
      </Form>
    )}
  />
)

export default RegisterDetailsForm
