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
            Coupon Names (each coupon at separate line)*
            <Field name="coupons" component="textarea" rows="4" cols="70" />   
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
