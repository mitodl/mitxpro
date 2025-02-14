import React from "react";
import { Formik, Field, Form, ErrorMessage } from "formik";
import * as yup from "yup";

import FormError from "./elements/FormError";

import { SHEET_IDENTIFIER_ID, SHEET_IDENTIFIER_TITLE } from "../../constants";

type CouponSheetProcessFormProps = {
  onSubmit: Function,
};

const couponValidations = yup.object().shape({
  sheet_identifier_value: yup
    .string()
    .required("Sheet ID or Title is required")
    .matches(
      /^[\w\n\s-]+$/,
      "Only letters, numbers, spaces, underscores, and hyphens allowed"
    ),
});

export const CouponSheetProcessForm = ({ onSubmit }: CouponSheetProcessFormProps) => {
  return (
    <Formik
      onSubmit={onSubmit}
      validationSchema={couponValidations}
      initialValues={{
        sheet_identifier_value: "",
        sheet_identifier_type: SHEET_IDENTIFIER_ID,
      }}
      render={({ isSubmitting, setFieldValue, values }) => (
        <Form className="coupon-form">
          <div>
            <div className="flex">
              <div>
                <Field
                  type="radio"
                  name="sheet_identifier_type"
                  value={SHEET_IDENTIFIER_ID}
                  onClick={() => setFieldValue("sheet_identifier_type", SHEET_IDENTIFIER_ID)}
                  checked={values.sheet_identifier_type===SHEET_IDENTIFIER_ID}
                />
                <label htmlFor="sheet_identifier_type">Use Sheet ID</label>
              </div>
              <div>
                <Field
                  type="radio"
                  name="sheet_identifier_type"
                  value={SHEET_IDENTIFIER_TITLE}
                  onClick={() => setFieldValue("sheet_identifier_type", SHEET_IDENTIFIER_TITLE)}
                  checked={values.sheet_identifier_type===SHEET_IDENTIFIER_TITLE}
                />
                <label htmlFor="sheet_identifier_type">Use Sheet Title</label>
                </div>
            </div>

            <div className="block text-area-div">
              <label htmlFor="sheet_identifier_value">
                {values.sheet_identifier_type===SHEET_IDENTIFIER_ID ? "Sheet ID*" : "Sheet Title*"}
                <Field name="sheet_identifier_value" component="textarea" rows="2" cols="40" />
              </label>
              <ErrorMessage name="sheet_identifier_value" component={FormError} />
            </div>
          </div>

          <div>
            <button type="submit" disabled={isSubmitting}>
              Process Coupon Sheet
            </button>
          </div>
        </Form>
      )}
    />
  );
};
