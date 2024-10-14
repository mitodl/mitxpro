// @flow
import React from "react";
import { Formik, Field, Form, ErrorMessage } from "formik";
import * as yup from "yup";

import FormError from "../../components/forms/elements/FormError";

type CouponDeactivateFormProps = {
  onSubmit: Function,
};

const couponValidations = yup.object().shape({
  coupons: yup
    .string()
    .required("At least one coupon name or code is required")
    .matches(/^[\w\n ]+$/, "Only letters, numbers, spaces and underscores allowed"),
});

export const CouponDeactivateForm = ({
  onSubmit,
}: CouponDeactivateFormProps) => (
  <Formik
    onSubmit={onSubmit}
    validationSchema={couponValidations}
    initialValues={{
      coupons: "",
    }}
    render={({ isSubmitting }) => (
      <Form className="coupon-form">
        <div>
          <div className="block text-area-div">
            <label htmlFor="coupons">
              Coupon Codes/Names (each code/name at a separate line)*
              <p className="small-text warning">
                Note: Adding coupon code like <strong>dd5475f4c1c</strong> will
                deactivate the specific coupon. Adding a coupon name like{" "}
                <strong>MIT_DIGITALLEARNING_25</strong> will deactivate all the
                coupon codes i.e. <strong>dd5475f4c1c ab064b8215f2 ...</strong>
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
