// @flow
import React from "react"
import { Formik, Form } from "formik"
import * as yup from "yup"

import { profileValidation, renderProfileFields } from "./ProfileFormFields"

type Props = {
  onSubmit: Function
}

const INITIAL_VALUES = {
  profile: {
    birth_year: "",
    gender:     "",
    company:    "",
    job_title:  ""
  }
}

const RegisterExtraDetailsForm = ({ onSubmit }: Props) => (
  <Formik
    onSubmit={onSubmit}
    validationSchema={yup.object().shape(profileValidation)}
    initialValues={INITIAL_VALUES}
    render={({ isSubmitting }) => (
      <Form>
        {renderProfileFields()}
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

export default RegisterExtraDetailsForm
