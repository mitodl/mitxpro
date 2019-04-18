// @flow
import React from "react"
import Picky from "react-picky"
import DayPickerInput from "react-day-picker/DayPickerInput"
import { Formik, Field, Form, ErrorMessage } from "formik"
import * as yup from "yup"

import type { Company, Product } from "../../flow/ecommerceTypes"

type CouponFormProps = {
  onSubmit: Function,
  toggleForm: Function,
  toggleProduct: Function,
  isPromo: boolean,
  companies: Array<Company>,
  products: Array<Product>,
  selectProducts: Function,
  selectedProducts: Array<Product>,
  productType: string
}

const baseValidations = {
  name: yup
    .string()
    .required("Coupon name is required")
    .matches(/^\w+$/, "Only letters, numbers, and underscores allowed"),
  products:        yup.array().min(1, "${min} or more products must be selected"),
  activation_date: yup.date().required("Valid activation date required"),
  expiration_date: yup.date().required("Valid expiration date required"),
  amount:          yup
    .number()
    .required("Percentage discount is required")
    .min(1, "Must be at least ${min}")
    .max(100, "Must be at most ${max}")
}

const promoValidations = yup.object(baseValidations).shape({
  max_redemptions: yup
    .number()
    .min(1, "Must be at least ${min}")
    .required("Number required"),
  coupon_code: yup
    .string()
    .required("Coupon code is required")
    .matches(/^\w+$/, "Only letters, numbers, and underscores allowed")
})

const singleUseValidations = yup.object(baseValidations).shape({
  num_coupon_codes: yup
    .number()
    .min(1, "Must be at least ${min}")
    .required("Number required"),
  payment_transaction: yup.string().required("Payment transaction is required"),
  payment_type:        yup.string().required("Payment type is required")
})

export const CouponForm = ({
  onSubmit,
  toggleForm,
  toggleProduct,
  isPromo,
  companies,
  products,
  productType,
  selectProducts,
  selectedProducts
}: CouponFormProps) => (
  <Formik
    onSubmit={onSubmit}
    validationSchema={isPromo ? promoValidations : singleUseValidations}
    initialValues={{
      coupon_type:         isPromo ? "promo" : "single-use",
      product_type:        productType,
      products:            [],
      amount:              "",
      name:                "",
      num_coupon_codes:    1,
      coupon_code:         "",
      activation_date:     "",
      expiration_dat:      "",
      payment_type:        "",
      payment_transaction: "",
      company:             ""
    }}
    render={({
      isSubmitting,
      setFieldValue,
      setFieldTouched,
      errors,
      touched
    }) => (
      <Form className="coupon-form">
        <div className="flex">
          <div>
            <Field
              type="radio"
              name="coupon_type"
              value="single-use"
              onClick={toggleForm}
              checked={!isPromo}
            />
            <label htmlFor="coupon_type">Coupon codes</label>
          </div>
          <div>
            <Field
              type="radio"
              name="coupon_type"
              value="promo"
              onClick={toggleForm}
              checked={isPromo}
            />
            <label htmlFor="coupon_type">Promo</label>
          </div>
        </div>

        <div className="block">
          {isPromo ? (
            <React.Fragment>
              <div>
                <label htmlFor="coupon_code">
                  Coupon code (letters, numbers, underscore only)*
                  <Field name="coupon_code" />
                </label>
                <ErrorMessage name="coupon_code" component="div" />
              </div>
              <div>
                <label htmlFor="max_redemptions">
                  Maximum redemptions*
                  <Field name="max_redemptions" />
                </label>
                <ErrorMessage name="max_redemptions" component="div" />
              </div>
            </React.Fragment>
          ) : (
            <React.Fragment>
              <label htmlFor="num_coupon_codes">
                Number of coupon codes*
                <Field name="num_coupon_codes" />
              </label>
              <ErrorMessage name="num_coupon_codes" component="div" />
            </React.Fragment>
          )}
        </div>

        <div>
          <div>
            <Field type="checkbox" name="automatic" />
            Automatically apply coupon to eligible products in basket
          </div>
          <div className="block">
            <label htmlFor="amount">
              Percentage Discount (1 to 100)*
              <Field name="amount" />
            </label>
            <ErrorMessage name="amount" component="div" />
          </div>
          <div className="block">
            <label htmlFor="name">
              Unique Coupon Name (letters, numbers, underscore only)*
              <Field name="name" />
            </label>
            <ErrorMessage name="name" component="div" />
          </div>
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
                format="MM/DD/YYYY"
                onDayChange={value => {
                  setFieldValue("activation_date", value)
                }}
                onDayPickerHide={() => setFieldTouched("activation_date")}
                error={errors.activation_date}
                touched={touched.activation_date}
              />
            </label>
            <ErrorMessage name="activation_date" component="div" />
          </div>
          <div className="block">
            <label htmlFor="expiration_date">
              Valid until*
              <DayPickerInput
                name="expiration_date"
                placeholder="DD/MM/YYYY"
                format="DD/MM/YYYY"
                onDayChange={value => {
                  setFieldValue("expiration_date", value)
                }}
                onDayPickerHide={() => setFieldTouched("expiration_date")}
                error={errors.expiration_date}
                touched={touched.expiration_date}
              />
            </label>
            <ErrorMessage name="expiration_date" component="div" />
          </div>
        </div>
        <div className="flex">
          <Field
            type="radio"
            name="product_type"
            value="program"
            onClick={toggleProduct}
            checked={productType === "program"}
          />
          Programs
          <Field
            type="radio"
            name="product_type"
            value="course"
            onClick={toggleProduct}
            checked={productType === "course"}
          />
          Courses
          <Field
            type="radio"
            name="product_type"
            value="courserun"
            onClick={toggleProduct}
            checked={productType === "courserun"}
          />
          Course runs
        </div>
        <ErrorMessage name="products" component="div" />
        <div className="product-selection">
          <Picky
            name="products"
            valueKey="id"
            labelKey="title"
            options={products}
            value={selectedProducts}
            open={true}
            multiple={true}
            includeSelectAll={false}
            includeFilter={true}
            onChange={value => {
              setFieldValue("products", value)
              setFieldTouched("products")
              selectProducts(value)
            }}
            dropdownHeight={200}
            className="product-picker"
          />
        </div>
        <div className="product-payment-info flex">
          <div className="block">
            <label htmlFor="payment_type">
              Payment type{isPromo ? null : "*"}
              <Field component="select" name="payment_type">
                <option value="">-----</option>
                <option value="credit_card">Credit Card</option>
                <option value="purchase_order">Purchase Order</option>
                <option value="sales">Sales</option>
                <option value="marketing">Marketing</option>
              </Field>
            </label>
            <ErrorMessage name="payment_type" component="div" />
          </div>
          <div className="block">
            <label htmlFor="payment_transaction">
              Transaction number{isPromo ? null : "*"}
              <Field name="payment_transaction" />
            </label>
            <ErrorMessage name="payment_transaction" component="div" />
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
          <ErrorMessage name="company" component="div" />
        </div>
        <button type="submit" disabled={isSubmitting}>
          Create coupons
        </button>
      </Form>
    )}
  />
)
