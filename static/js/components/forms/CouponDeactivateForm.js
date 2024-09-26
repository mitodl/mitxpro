// @flow
import React from "react";
import { Formik, Field, Form, ErrorMessage } from "formik";
import * as yup from "yup";

import FormError from "../../components/forms/elements/FormError";

type CouponDeactvateFormProps = {
  onSubmit: Function,
};

const couponValidations = yup.object().shape({
  coupons: yup
    .string()
    .required("At least one coupon name is required")
    .matches(/^[\w\n]+$/, "Only letters, numbers, and underscores allowed"),
});

export const CouponDeactivateForm = ({
  onSubmit,
}: CouponDeactvateFormProps) => (
  <Formik
    onSubmit={onSubmit}
    validationSchema={couponValidations}
    initialValues={{
      coupons: "",
    }}
    render={({
      isSubmitting,
      setFieldValue,
      setFieldTouched,
      errors,
      touched,
      values,
    }) => (
      <Form className="coupon-form">
        <div>
          <div className="block text-area-div">
            <label htmlFor="coupons">
              Coupon Codes/Names (each coupon at a separate line)*
              <p className="small-text">
                Note: Adding a coupon name will deactivate all coupon codes
                associated with that name.
              </p>
              <Field name="coupons" component="textarea" rows="4" />
            </label>
            <ErrorMessage name="coupons" component={FormError} />
          </div>
        </div>

        <div>
          <button type="submit" disabled={isSubmitting}>
            Deactivate coupons
          </button>
        </div>
      </Form>
    )}
  />
);
