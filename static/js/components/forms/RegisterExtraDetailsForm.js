// @flow
import React from "react"
import * as yup from "yup"
import { range, reverse } from "ramda"
import moment from "moment"
import { Formik, Field, Form, ErrorMessage } from "formik"
import FormError from "./FormError"
import {
  EMPLOYMENT_INDUSTRY,
  EMPLOYMENT_FUNCTION,
  EMPLOYMENT_EXPERIENCE,
  EMPLOYMENT_SIZE,
  EMPLOYMENT_LEVEL
} from "../../constants"

const seedYear = moment().year()

const extraDetailsValidation = yup.object().shape({
  gender: yup
    .string()
    .label("Gender")
    .required(),
  birth_year: yup
    .number()
    .label("Birth Year")
    .required(),
  company: yup
    .string()
    .label("Company")
    .required(),
  job_title: yup
    .string()
    .label("Job Title")
    .required()
})

type Props = {
  onSubmit: Function
}

const INITIAL_VALUES = {
  birth_year: "",
  gender:     "",
  company:    "",
  job_title:  ""
}

const RegisterExtraDetailsForm = ({ onSubmit }: Props) => (
  <Formik
    onSubmit={onSubmit}
    validationSchema={extraDetailsValidation}
    initialValues={INITIAL_VALUES}
    render={({ isSubmitting, isValid }) => (
      <Form>
        <div className="form-group">
          <div className="row">
            <div className="col">
              <label htmlFor="gender" className="font-weight-bold">
                Gender*
              </label>

              <Field component="select" name="gender" className="form-control">
                <option value="">-----</option>
                <option value="f">Female</option>
                <option value="m">Male</option>
                <option value="o">Other / Prefer not to say</option>
              </Field>
              <ErrorMessage name="gender" component={FormError} />
            </div>
            <div className="col">
              <label htmlFor="birth_year" className="font-weight-bold">
                Year of Birth*
              </label>
              <Field
                component="select"
                name="birth_year"
                className="form-control"
              >
                <option value="">-----</option>
                {reverse(range(seedYear - 120, seedYear - 14)).map(
                  (year, i) => (
                    <option key={i} value={year}>
                      {year}
                    </option>
                  )
                )}
              </Field>
              <ErrorMessage name="birth_year" component={FormError} />
            </div>
          </div>
        </div>
        <div className="form-group">
          <label htmlFor="company" className="font-weight-bold">
            Company*
          </label>
          <Field type="text" name="company" className="form-control" />
          <ErrorMessage name="company" component={FormError} />
        </div>
        <div className="form-group">
          <label htmlFor="job_title" className="font-weight-bold">
            Job Title*
          </label>
          <Field type="text" name="job_title" className="form-control" />
          <ErrorMessage name="job_title" component={FormError} />
        </div>
        <div className="form-group dotted" />
        <div className="form-group">
          <label htmlFor="industry" className="font-weight-bold">
            Industry
          </label>
          <Field component="select" name="industry" className="form-control">
            <option value="">-----</option>
            {EMPLOYMENT_INDUSTRY.map((industry, i) => (
              <option key={i} value={industry}>
                {industry}
              </option>
            ))}
          </Field>
        </div>
        <div className="form-group">
          <label htmlFor="job_function" className="font-weight-bold">
            Job Function
          </label>
          <Field
            component="select"
            name="job_function"
            className="form-control"
          >
            <option value="">-----</option>
            {EMPLOYMENT_FUNCTION.map((jobFunction, i) => (
              <option key={i} value={jobFunction}>
                {jobFunction}
              </option>
            ))}
          </Field>
        </div>
        <div className="form-group">
          <label htmlFor="company_size" className="font-weight-bold">
            Company Size
          </label>
          <Field
            component="select"
            name="company_size"
            className="form-control"
          >
            <option value="">-----</option>
            {EMPLOYMENT_SIZE.map(([value, label], i) => (
              <option key={i} value={value}>
                {label}
              </option>
            ))}
          </Field>
        </div>
        <div className="form-group">
          <div className="row">
            <div className="col">
              <label htmlFor="years_experience" className="font-weight-bold">
                Years of Work Experience
              </label>
              <Field
                component="select"
                name="years_experience"
                className="form-control"
              >
                <option value="">-----</option>
                {EMPLOYMENT_EXPERIENCE.map(([value, label], i) => (
                  <option key={i} value={value}>
                    {label}
                  </option>
                ))}
              </Field>
            </div>
            <div className="col">
              <label htmlFor="leadership_level" className="font-weight-bold">
                Leadership Level
              </label>
              <Field
                component="select"
                name="leadership_level"
                className="form-control"
              >
                <option value="">-----</option>
                {EMPLOYMENT_LEVEL.map((level, i) => (
                  <option key={i} value={level}>
                    {level}
                  </option>
                ))}
              </Field>
            </div>
          </div>
        </div>

        <div className="row justify-content-end">
          <div className="row justify-content-end">
            <button
              type="submit"
              disabled={isSubmitting || !isValid}
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

export default RegisterExtraDetailsForm
