// @flow
import React from "react"
import { Formik, Form } from "formik"
import * as yup from "yup"
import { mergeDeepRight } from "ramda"

import {
  passwordValidation,
  legalAddressValidation,
  renderLegalAddressFields
} from "./ProfileFormFields"

import type { Country } from "../../flow/authTypes"

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
    validationSchema={yup
      .object()
      .shape(mergeDeepRight(legalAddressValidation, passwordValidation))}
    initialValues={INITIAL_VALUES}
    render={({ isSubmitting, setFieldValue, setFieldTouched, values }) => (
      <Form>
        {renderLegalAddressFields(
          countries,
          setFieldValue,
          setFieldTouched,
          values,
          true
        )}
        <div className="row submit-row no-gutters justify-content-end">
          <button
            type="submit"
            className="btn btn-primary btn-light-blue"
            disabled={isSubmitting}
          >
            Continue
          </button>
        </div>
      </Form>
    )}
  />
)

export default RegisterDetailsForm
