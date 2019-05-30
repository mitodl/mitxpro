// @flow
import React from "react"
import { Formik, Form } from "formik"

import {
  profileValidation,
  legalAddressValidation,
  LegalAddressFields,
  ProfileFields
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
    validationSchema={legalAddressValidation.concat(profileValidation)}
    initialValues={getInitialValues(user)}
    render={({ isSubmitting, setFieldValue, setFieldTouched, values }) => (
      <Form>
        <LegalAddressFields
          countries={countries}
          setFieldValue={setFieldValue}
          setFieldTouched={setFieldTouched}
          values={values}
          includePassword={false}
        />
        <ProfileFields />
        <div className="row-inner justify-content-end">
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
