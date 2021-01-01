// @flow
import React from "react"
import moment from "moment"
import Picky from "react-picky"
import { filter, pathSatisfies, equals, always, sortBy, prop } from "ramda"
import { formatDate, parseDate } from "react-day-picker/moment"
import DayPickerInput from "react-day-picker/DayPickerInput"
import { Formik, Field, Form, ErrorMessage } from "formik"
import * as yup from "yup"

import {
  COUPON_TYPE_PROMO,
  COUPON_TYPE_SINGLE_USE,
  PRODUCT_TYPE_COURSERUN,
  PRODUCT_TYPE_PROGRAM
} from "../../constants"
import { isPromo } from "../../lib/ecommerce"
import { getProductSelectLabel } from "../../lib/util"
import FormError from "../../components/forms/elements/FormError"

import type { Company, Product } from "../../flow/ecommerceTypes"

type CouponFormProps = {
  onSubmit: Function,
  companies: Array<Company>,
  products: Array<Product>
}

const couponValidations = yup.object().shape({
  name: yup
    .string()
    .required("Coupon name is required")
    .matches(/^\w+$/, "Only letters, numbers, and underscores allowed"),
  coupon_type: yup.string().required("Coupon type is required"),
  products:    yup.array().when("is_global", {
    is:   false,
    then: yup.array().min(1, "${min} or more products must be selected")
  }),
  is_global:       yup.boolean(),
  activation_date: yup.date().required("Valid activation date required"),
  expiration_date: yup
    .date()
    .min(
      moment.max(yup.ref("activation_date"), moment()),
      "Expiration date must be after today/activation date"
    )
    .required("Valid expiration date required"),
  discount: yup
    .number()
    .required("Percentage discount is required")
    .min(1, "Must be at least ${min}")
    .max(100, "Must be at most ${max}"),
  max_redemptions: yup.number().when("coupon_type", {
    is:   COUPON_TYPE_PROMO,
    then: yup
      .number()
      .min(1, "Must be at least ${min}")
      .required("Number required")
  }),
  coupon_code: yup.string().when("coupon_type", {
    is:   COUPON_TYPE_PROMO,
    then: yup
      .string()
      .required("Coupon code is required")
      .matches(/^\w+$/, "Only letters, numbers, and underscores allowed")
  }),
  num_coupon_codes: yup.number().when("coupon_type", {
    is:   COUPON_TYPE_SINGLE_USE,
    then: yup
      .number()
      .min(1, "Must be at least ${min}")
      .required("Number required")
  }),
  max_redemptions_per_user: yup.number().when("coupon_type", {
    is:   COUPON_TYPE_PROMO,
    then: yup
      .number()
      .required("Number required")
      .min(1, "Must be at least ${min}")
      .max(100, "Must be at most ${max}")
  }),
  payment_transaction: yup.string().when("coupon_type", {
    is:   COUPON_TYPE_SINGLE_USE,
    then: yup.string().required("Payment transaction is required")
  }),
  payment_type: yup.string().when("coupon_type", {
    is:   COUPON_TYPE_SINGLE_USE,
    then: yup.string().required("Payment type is required")
  })
})

const zeroHour = value => {
  if (value instanceof Date) {
    value.setHours(0, 0, 0, 0)
  }
}

const finalHour = value => {
  if (value instanceof Date) {
    value.setHours(23, 59, 59, 999)
  }
}

export const CouponForm = ({
  onSubmit,
  companies,
  products
}: CouponFormProps) => (
  <Formik
    onSubmit={onSubmit}
    validationSchema={couponValidations}
    initialValues={{
      coupon_type:              COUPON_TYPE_SINGLE_USE,
      product_type:             PRODUCT_TYPE_COURSERUN,
      products:                 [],
      num_coupon_codes:         1,
      max_redemptions:          1000000,
      max_redemptions_per_user: 1,
      discount:                 "",
      name:                     "",
      coupon_code:              "",
      activation_date:          "",
      expiration_date:          "",
      company:                  "",
      payment_type:             "",
      payment_transaction:      "",
      include_future_runs:      false,
      is_global:                false
    }}
    render={({
      isSubmitting,
      setFieldValue,
      setFieldTouched,
      errors,
      touched,
      values
    }) => (
      <Form className="coupon-form">
        <div className="flex">
          <div>
            <Field
              type="radio"
              name="coupon_type"
              value={COUPON_TYPE_SINGLE_USE}
              checked={!isPromo(values.coupon_type)}
            />
            <label htmlFor="coupon_type">Coupon codes</label>
          </div>
          <div>
            <Field
              type="radio"
              name="coupon_type"
              value={COUPON_TYPE_PROMO}
              checked={isPromo(values.coupon_type)}
            />
            <label htmlFor="coupon_type">Promo</label>
          </div>
        </div>

        <div className="block">
          {isPromo(values.coupon_type) ? (
            <React.Fragment>
              <div>
                <label htmlFor="coupon_code">
                  Coupon code (letters, numbers, underscore only)*
                  <Field name="coupon_code" />
                </label>
                <ErrorMessage name="coupon_code" component={FormError} />
              </div>
              <div>
                <label htmlFor="max_redemptions">
                  Maximum redemptions*
                  <Field name="max_redemptions" />
                </label>
                <ErrorMessage name="max_redemptions" component={FormError} />
              </div>
            </React.Fragment>
          ) : (
            <React.Fragment>
              <label htmlFor="num_coupon_codes">
                Number of coupon codes*
                <Field name="num_coupon_codes" />
              </label>
              <ErrorMessage name="num_coupon_codes" component={FormError} />
            </React.Fragment>
          )}
        </div>

        <div>
          <div className="block">
            <label htmlFor="discount">
              Percentage Discount (1 to 100)*
              <Field name="discount" />
            </label>
            <ErrorMessage name="discount" component={FormError} />
          </div>
          <div className="block">
            <label htmlFor="name">
              Unique Coupon Name (letters, numbers, underscore only)*
              <Field name="name" />
            </label>
            <ErrorMessage name="name" component={FormError} />
          </div>
          {isPromo(values.coupon_type) && (
            <div className="block">
              <label htmlFor="max_redemptions_per_user">
                Max Redemptions Per User (1 to 100)*
                <Field name="max_redemptions_per_user" />
              </label>
              <ErrorMessage
                name="max_redemptions_per_user"
                component={FormError}
              />
            </div>
          )}
          <div className="block">
            <label htmlFor="tag">
              Tag (optional)
              <Field name="tag" />
            </label>
          </div>
        </div>
        <div className="flex">
          <div className="block">
            <label htmlFor="activation_date">
              Valid from*
              <DayPickerInput
                name="activation_date"
                placeholder="MM/DD/YYYY"
                format="L"
                formatDate={formatDate}
                parseDate={parseDate}
                onDayChange={value => {
                  zeroHour(value)
                  setFieldValue("activation_date", value)
                }}
                onDayPickerHide={() => setFieldTouched("activation_date")}
                error={errors.activation_date}
                touched={touched.activation_date}
              />
            </label>
            <ErrorMessage name="activation_date" component={FormError} />
          </div>
          <div className="block">
            <label htmlFor="expiration_date">
              Valid until*
              <DayPickerInput
                name="expiration_date"
                placeholder="MM/DD/YYYY"
                format="L"
                formatDate={formatDate}
                parseDate={parseDate}
                onDayChange={value => {
                  finalHour(value)
                  setFieldValue("expiration_date", value)
                }}
                onDayPickerHide={() => setFieldTouched("expiration_date")}
                error={errors.expiration_date}
                touched={touched.expiration_date}
              />
            </label>
            <ErrorMessage name="expiration_date" component={FormError} />
          </div>
        </div>
        <div className={values.is_global ? "flex disabled" : "flex"}>
          <label htmlFor="include_future_runs">
            <Field
              type="checkbox"
              name="include_future_runs"
              checked={values.include_future_runs}
              disabled={values.is_global}
            />
            Include future runs
          </label>
        </div>
        <div className={values.include_future_runs ? "flex disabled" : "flex"}>
          <label htmlFor="is_global">
            <Field
              type="checkbox"
              name="is_global"
              checked={values.is_global}
              onChange={() => {
                values.is_global = !values.is_global
                setFieldValue("is_global", values.is_global)
                if (values.is_global) {
                  setFieldValue("products", [])
                  setFieldTouched("products")
                }
              }}
              disabled={values.include_future_runs}
            />
            Global coupon (applies to all products)
          </label>
        </div>
        <div className="flex" hidden={values.is_global}>
          <Field
            type="radio"
            name="product_type"
            value={PRODUCT_TYPE_PROGRAM}
            onClick={evt => {
              setFieldValue("product_type", evt.target.value)
              setFieldValue("products", [])
            }}
            checked={values.product_type === PRODUCT_TYPE_PROGRAM}
          />
          Programs
          <Field
            type="radio"
            name="product_type"
            value={PRODUCT_TYPE_COURSERUN}
            onClick={evt => {
              setFieldValue("product_type", evt.target.value)
              setFieldValue("products", [])
            }}
            checked={values.product_type === PRODUCT_TYPE_COURSERUN}
          />
          Course runs
          <Field
            type="radio"
            name="product_type"
            value=""
            onClick={evt => {
              setFieldValue("product_type", evt.target.value)
              setFieldValue("products", [])
            }}
            checked={values.product_type === ""}
          />
          All products
        </div>
        <ErrorMessage name="products" component={FormError} />
        <div className="product-selection" hidden={values.is_global}>
          <Picky
            name="products"
            valueKey="id"
            labelKey="label"
            options={filter(
              values.product_type
                ? pathSatisfies(equals(values.product_type), ["product_type"])
                : always(true),
              sortBy(
                prop("label"),
                (products || []).map(product => ({
                  ...product,
                  label: getProductSelectLabel(product)
                }))
              )
            )}
            value={values.products}
            open={true}
            multiple={true}
            includeSelectAll={false}
            includeFilter={true}
            onChange={value => {
              setFieldValue("products", value)
              setFieldTouched("products")
            }}
            dropdownHeight={200}
            className="product-picker"
          />
        </div>
        <div className="product-payment-info flex">
          <div className="block">
            <label htmlFor="payment_type">
              Payment type{isPromo(values.coupon_type) ? null : "*"}
              <Field component="select" name="payment_type">
                <option value="">-----</option>
                <option value="credit_card">Credit Card</option>
                <option value="purchase_order">Purchase Order</option>
                <option value="sales">Sales</option>
                <option value="marketing">Marketing</option>
                <option value="staff">Staff</option>
              </Field>
            </label>
            <ErrorMessage name="payment_type" component={FormError} />
          </div>
          <div className="block">
            <label htmlFor="payment_transaction">
              Transaction number{isPromo(values.coupon_type) ? null : "*"}
              <Field name="payment_transaction" />
            </label>
            <ErrorMessage name="payment_transaction" component={FormError} />
          </div>
        </div>
        <div className="product-company block">
          <label htmlFor="company">
            Company
            <Field component="select" name="company">
              <option value="">-----</option>
              {companies
                ? companies.map((company, i) => (
                  <option key={i} value={company.id}>
                    {company.name}
                  </option>
                ))
                : null}
            </Field>
          </label>
          <ErrorMessage name="company" component={FormError} />
        </div>
        <div className="block">
          <div className="dangerous">
            <strong>⚠️WARNING: You probably do not want this option. ⚠️</strong>
            <br />
            <br />
            Enabling this option will automatically apply this code to{" "}
            <strong>EVERY USER</strong> who purchases this course run/program.
            In other words, the code will be automatically applied and they will
            not need to enter any coupon code during checkout.
          </div>
          <div className="flex dangerous">
            <Field type="checkbox" name="automatic" />
            Automatically apply coupon to eligible products in basket
          </div>
        </div>
        <div>
          <button type="submit" disabled={isSubmitting}>
            Create coupons
          </button>
        </div>
      </Form>
    )}
  />
)
