// @flow
/* global SETTINGS:false */
import React from "react";

import { Formik, Field, Form, ErrorMessage } from "formik";

import { PasswordInput } from "./elements/inputs";
import FormError from "./elements/FormError";
import { changePasswordFormValidation } from "../../lib/validation";

type Props = {
  onSubmit: Function,
};

export type ChangePasswordFormValues = {
  oldPassword: string,
  newPassword: string,
  confirmPassword: string,
};

const ChangePasswordForm = ({ onSubmit }: Props) => (
  <Formik
    onSubmit={onSubmit}
    validationSchema={changePasswordFormValidation}
    initialValues={{
      oldPassword: "",
      newPassword: "",
      confirmPassword: "",
    }}
  >
    {({ isSubmitting }) => (
      <Form>
        <section className="email-section">
          <h4>Change Password</h4>
          <div className="form-group">
            <label htmlFor="oldPassword">Old Password</label>
            <Field
              name="oldPassword"
              className="form-control"
              component={PasswordInput}
            />
            <ErrorMessage name="oldPassword" component={FormError} />
          </div>
          <div className="form-group">
            <label htmlFor="newPassword">New Password</label>
            <Field
              name="newPassword"
              className="form-control"
              component={PasswordInput}
            />
            <ErrorMessage name="newPassword" component={FormError} />
          </div>
          <div className="form-group">
            <label htmlFor="confirmPassword">Confirm Password</label>
            <Field
              name="confirmPassword"
              className="form-control"
              component={PasswordInput}
            />
            <ErrorMessage name="confirmPassword" component={FormError} />
          </div>
        </section>
        <div className="row submit-row no-gutters justify-content-end">
          <button
            type="submit"
            className="btn btn-primary btn-light-blue"
            disabled={isSubmitting}
          >
            Submit
          </button>
        </div>
      </Form>
    )}
  </Formik>
);

export default ChangePasswordForm;
