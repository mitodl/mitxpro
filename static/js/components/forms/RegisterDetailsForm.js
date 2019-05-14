// @flow
import React from "react"
import * as yup from "yup"
import { __, includes, find, propEq } from "ramda"

import { Formik, Field, Form, ErrorMessage, FieldArray } from "formik"
import type { Country } from "../../flow/authTypes"
import FormError from "./FormError"

const US_ALPHA_2 = "US"
const CA_ALPHA_2 = "CA"

const US_POSTAL_CODE_REGEX = /[0-9]{5}(-[0-9]{4}){0,1}/
const CA_POSTAL_CODE_REGEX = /[A-Z][0-9][A-Z] [0-9][A-Z][0-9]/
const COUNTRIES_REQUIRING_POSTAL_CODE = [US_ALPHA_2, CA_ALPHA_2]
const COUNTRIES_REQUIRING_STATE = [US_ALPHA_2, CA_ALPHA_2]

const ADDRESS_LINES_MAX = 4

const detailsValidation = yup.object().shape({
  name: yup
    .string()
    .label("Legal Name")
    .trim()
    .required(),
  password: yup
    .string()
    .label("Password")
    .required()
    .min(8)
    .matches(/^(?=.*[0-9])(?=.*[a-zA-Z]).*$/, {
      message: "Password must contain at least one letter and number"
    }),
  legal_address: yup.object().shape({
    first_name: yup
      .string()
      .label("First Name")
      .trim()
      .required(),
    last_name: yup
      .string()
      .label("Last Name")
      .trim()
      .required(),
    city: yup
      .string()
      .label("City")
      .trim()
      .required(),
    street_address: yup
      .array()
      .label("Street address")
      .of(yup.string().max(60))
      .min(1)
      .max(ADDRESS_LINES_MAX)
      .compact()
      .required(),
    state_or_territory: yup
      .mixed()
      .label("State/Territory")
      .when("country", {
        is:   includes(__, COUNTRIES_REQUIRING_STATE),
        then: yup.string().required()
      }),
    country: yup
      .string()
      .label("Country")
      .length(2)
      .required(),
    postal_code: yup
      .string()
      .label("Zip/Postal Code")
      .trim()
      .when("country", (country, schema) => {
        if (country === US_ALPHA_2) {
          return schema.required().matches(US_POSTAL_CODE_REGEX, {
            message:
              "Postal Code must be formatted as either 'NNNNN' or 'NNNNN-NNNN'"
          })
        } else if (country === CA_ALPHA_2) {
          return schema.required().matches(CA_POSTAL_CODE_REGEX, {
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
    street_address:     ["", ""],
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
    render={({ isSubmitting, setFieldValue, setFieldTouched, values }) => (
      <Form>
        <div className="form-group">
          <label htmlFor="legal_address.last_name" className="font-weight-bold">
            Legal Name*
          </label>
          <Field type="text" name="name" className="form-control" />
          <ErrorMessage name="name" component={FormError} />
        </div>
        <div className="form-group">
          <label htmlFor="legal_address.first_name" className="row">
            <div className="col-4 font-weight-bold">First Name*</div>
            <div className="col-8">(Name that will appear on emails)</div>
          </label>
          <Field
            type="text"
            name="legal_address.first_name"
            className="form-control"
          />
          <ErrorMessage name="legal_address.first_name" component={FormError} />
        </div>
        <div className="form-group">
          <label htmlFor="legal_address.last_name" className="font-weight-bold">
            Last Name*
          </label>
          <Field
            type="text"
            name="legal_address.last_name"
            className="form-control"
          />
          <ErrorMessage name="legal_address.last_name" component={FormError} />
        </div>
        <div className="form-group">
          <label htmlFor="password" className="font-weight-bold">
            Password*
          </label>
          <Field type="password" name="password" className="form-control" />
          <ErrorMessage name="password" component={FormError} />
          <div className="label-secondary">
            Password must contain:
            <ul>
              <li>at least 8 characters</li>
              <li>at least 1 number and 1 letter</li>
            </ul>
          </div>
        </div>
        <div className="form-group">
          {/* LegalAddress fields */}
          <label htmlFor="legal_address.last_name" className="font-weight-bold">
            Street Address*
          </label>
          <FieldArray
            name="legal_address.street_address"
            render={arrayHelpers => (
              <div>
                {values.legal_address.street_address.map((line, index) => (
                  <div key={index}>
                    <Field
                      name={`legal_address.street_address[${index}]`}
                      className={`form-control ${index > 0 ? "row-inner" : ""}`}
                    />
                    {index === 0 ? (
                      <ErrorMessage
                        name="legal_address.street_address"
                        component={FormError}
                      />
                    ) : null}
                  </div>
                ))}
                {values.legal_address.street_address.length <
                ADDRESS_LINES_MAX ? (
                    <button
                      type="button"
                      className="additional-street"
                      onClick={() => arrayHelpers.push("")}
                    >
                    Add additional line
                    </button>
                  ) : null}
              </div>
            )}
          />
        </div>
        <div className="form-group">
          <label className="font-weight-bold">Country*</label>
          <Field
            component="select"
            name="legal_address.country"
            className="form-control"
            onChange={e => {
              setFieldValue("legal_address.country", e.target.value)
              setFieldTouched("legal_address.country")
              if (!includes(e.target.value, [US_ALPHA_2, CA_ALPHA_2])) {
                setFieldValue("legal_address.state_or_territory", "")
                setFieldValue("legal_address.postal_code", "")
              }
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
          <ErrorMessage name="legal_address.country" component={FormError} />
        </div>
        {includes(values.legal_address.country, COUNTRIES_REQUIRING_STATE) ? (
          <div className="form-group">
            <label className="font-weight-bold">State/Province*</label>
            <Field
              component="select"
              name="legal_address.state_or_territory"
              className="form-control"
            >
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
            <ErrorMessage
              name="legal_address.state_or_territory"
              component={FormError}
            />
          </div>
        ) : null}
        <div className="form-group">
          <label htmlFor="legal_address.city" className="font-weight-bold">
            City*
          </label>
          <Field
            type="text"
            name="legal_address.city"
            className="form-control"
          />
          <ErrorMessage name="legal_address.city" component={FormError} />
        </div>
        {includes(
          values.legal_address.country,
          COUNTRIES_REQUIRING_POSTAL_CODE
        ) ? (
            <div className="form-group">
              <label
                htmlFor="legal_address.postal_code"
                className="font-weight-bold"
              >
              Zip/Postal Code*
              </label>
              <Field
                type="text"
                name="legal_address.postal_code"
                className="form-control"
              />
              <ErrorMessage
                name="legal_address.postal_code"
                component={FormError}
              />
            </div>
          ) : null}
        <div className="row-inner  justify-content-end">
          <div className="row justify-content-end">
            <button
              type="submit"
              disabled={isSubmitting}
              className="btn btn-primary btn-light-blue"
            >
              Continue
            </button>
          </div>
        </div>
      </Form>
    )}
  />
)

export default RegisterDetailsForm
