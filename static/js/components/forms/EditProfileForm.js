// @flow
import React from "react"
import { Formik, Form } from "formik"
import * as yup from "yup"
import { mergeDeepRight } from "ramda"
import {
  extraDetailsValidation,
  primaryDetailsValidation,
  renderProfileFields,
  renderLegalAddressFields
} from "./ProfileFormFields"

import type { Country, User } from "../../flow/authTypes"

type Props = {
  onSubmit: Function,
  countries: Array<Country>,
  user: User
}

const getInitialValues = (user: User) => ({
  name:          user.name,
  email:         user.email,
  legal_address: user.legal_address,
  profile:       user.profile
})

const EditProfileForm = ({ onSubmit, countries, user }: Props) => (
  <Formik
    onSubmit={onSubmit}
    validationSchema={yup
      .object()
      .shape(mergeDeepRight(primaryDetailsValidation, extraDetailsValidation))}
    initialValues={getInitialValues(user)}
    render={({ isSubmitting, setFieldValue, setFieldTouched, values }) => (
      <Form>
        {countries
          ? renderLegalAddressFields(
            countries,
            setFieldValue,
            setFieldTouched,
            values,
            false
          )
          : null}
        {renderProfileFields()}
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

export default EditProfileForm
