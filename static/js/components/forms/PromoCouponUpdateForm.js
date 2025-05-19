// @flow
import React from "react";
import moment from "moment";
import { Picky } from "react-picky";
import { filter, pathSatisfies, equals, always, sortBy, prop } from "ramda";
import { formatDate, parseDate } from "react-day-picker/moment";
import DayPickerInput from "react-day-picker/DayPickerInput";
import { Formik, Field, Form, ErrorMessage } from "formik";
import * as yup from "yup";

import { PRODUCT_TYPE_COURSERUN, PRODUCT_TYPE_PROGRAM } from "../../constants";
import { getProductSelectLabel } from "../../lib/util";
import FormError from "./elements/FormError";

import type { Company, Product } from "../../flow/ecommerceTypes";

type PromoCouponUpdateFormProps = {
  onSubmit: Function,
  companies: Array<Company>,
  products: Array<Product>,
};

const couponValidations = yup.object().shape({
  promo_coupon: yup.string().required("Promo coupon is required"),
  activation_date: yup.date().required("Valid activation date required"),
  expiration_date: yup
    .date()
    .min(
      moment.max(yup.ref("activation_date"), moment()),
      "Expiration date must be after today/activation date",
    )
    .required("Valid expiration date required"),
  products: yup.array().min(1, "${min} or more products must be selected"),
});

const selectProducts = (coupon, products) => {
  const productIds = coupon.eligibility.map((product) => product.product_id);
  const selectedProducts = products
    .filter((product) => productIds.includes(product.id))
    .map((product) => ({
      ...product,
      label: getProductSelectLabel(product),
    }));
  return selectedProducts;
};

const zeroHour = (value) => {
  if (value instanceof Date) {
    value.setHours(0, 0, 0, 0);
  }
};

const finalHour = (value) => {
  if (value instanceof Date) {
    value.setHours(23, 59, 59, 999);
  }
};

export const PromoCouponUpdateForm = ({
  onSubmit,
  promoCoupons,
  products,
}: PromoCouponUpdateFormProps) => {
  return (
    <Formik
      onSubmit={onSubmit}
      validationSchema={couponValidations}
      initialValues={{
        promo_coupon: "",
        product_type: "",
        products: [],
        activation_date: "",
        expiration_date: "",
        productSelectionsByType: {
          [PRODUCT_TYPE_COURSERUN]: [],
          [PRODUCT_TYPE_PROGRAM]: [],
          "": [],
        },
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
          <div className="block">
            <label htmlFor="promo_coupon">
              Promo Coupon
              <Field
                component="select"
                name="promo_coupon"
                onChange={(e) => {
                  const selectedId = e.target.value;
                  setFieldValue("promo_coupon", selectedId);
                  const selectedCoupon = promoCoupons?.find(
                    (coupon) => String(coupon.id) === selectedId,
                  );
                  if (selectedCoupon) {
                    const activationDate = moment(
                      selectedCoupon.activation_date,
                    ).toDate();
                    const expirationDate = moment(
                      selectedCoupon.expiration_date,
                    ).toDate();
                    const selectedProducts = selectProducts(
                      selectedCoupon,
                      products,
                    );

                    zeroHour(activationDate);
                    finalHour(expirationDate);

                    setFieldValue("activation_date", activationDate);
                    setFieldValue("expiration_date", expirationDate);
                    // setFieldValue("products", selectedProducts);
                    // Save selected products by product_type
                    const grouped = {
                      [PRODUCT_TYPE_COURSERUN]: [],
                      [PRODUCT_TYPE_PROGRAM]: [],
                      "": [],
                    };
                    selectedProducts.forEach((product) => {
                      grouped[product.product_type]?.push(product);
                      grouped[""].push(product);
                    });

                    Object.entries(grouped).forEach(([type, prods]) => {
                      setFieldValue(`productSelectionsByType.${type}`, prods);
                    });
                    setFieldValue("products", grouped[values.product_type]);
                  }
                }}
              >
                <option value="">-----</option>
                {promoCoupons?.map((promoCoupon) => (
                  <option key={promoCoupon.id} value={promoCoupon.id}>
                    {promoCoupon.coupon_code}
                  </option>
                ))}
              </Field>
            </label>
            <ErrorMessage name="promo_coupon" component={FormError} />
          </div>
          <div className="flex">
            <div className="block">
              <label htmlFor="activation_date">
                Valid from*
                <DayPickerInput
                  name="activation_date"
                  placeholder="MM/DD/YYYY"
                  value={values.activation_date}
                  format="L"
                  formatDate={formatDate}
                  parseDate={parseDate}
                  onDayChange={(value) => {
                    zeroHour(value);
                    setFieldValue("activation_date", value);
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
                  value={values.expiration_date}
                  format="L"
                  formatDate={formatDate}
                  parseDate={parseDate}
                  onDayChange={(value) => {
                    finalHour(value);
                    setFieldValue("expiration_date", value);
                  }}
                  onDayPickerHide={() => setFieldTouched("expiration_date")}
                  error={errors.expiration_date}
                  touched={touched.expiration_date}
                />
              </label>
              <ErrorMessage name="expiration_date" component={FormError} />
            </div>
          </div>
          <div className="flex">
            <Field
              type="radio"
              name="product_type"
              value={PRODUCT_TYPE_PROGRAM}
              onClick={(evt) => {
                const newProductType = evt.target.value;
                setFieldValue("product_type", newProductType);

                const cached =
                  values.productSelectionsByType?.[newProductType] || [];
                setFieldValue("products", cached);
              }}
              checked={values.product_type === PRODUCT_TYPE_PROGRAM}
            />
            Programs
            <Field
              type="radio"
              name="product_type"
              value={PRODUCT_TYPE_COURSERUN}
              onClick={(evt) => {
                const newProductType = evt.target.value;
                setFieldValue("product_type", newProductType);

                const cached =
                  values.productSelectionsByType?.[newProductType] || [];
                setFieldValue("products", cached);
              }}
              checked={values.product_type === PRODUCT_TYPE_COURSERUN}
            />
            Course runs
            <Field
              type="radio"
              name="product_type"
              value=""
              onClick={(evt) => {
                const newProductType = evt.target.value;
                setFieldValue("product_type", newProductType);

                // Merge both program + course run selections
                const courseRun =
                  values.productSelectionsByType?.[PRODUCT_TYPE_COURSERUN] ||
                  [];
                const program =
                  values.productSelectionsByType?.[PRODUCT_TYPE_PROGRAM] || [];

                // Combine and dedupe by product id
                const merged = [...courseRun, ...program].filter(
                  (prod, index, self) =>
                    index === self.findIndex((p) => p.id === prod.id),
                );

                setFieldValue("products", merged);
              }}
              checked={values.product_type === ""}
            />
            All products
          </div>
          {values.product_type != "" && (
            <p className="small-text warning">
              {" "}
              Switch to All Products to select both course runs and
              programs.{" "}
            </p>
          )}
          <ErrorMessage name="products" component={FormError} />
          <div className="product-selection">
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
                  (products || []).map((product) => ({
                    ...product,
                    label: getProductSelectLabel(product),
                  })),
                ),
              )}
              value={values.products}
              open={true}
              multiple={true}
              includeSelectAll={false}
              includeFilter={true}
              placeholder="Select products"
              onChange={(value) => {
                setFieldValue("products", value);
                setFieldTouched("products");

                if (values.product_type === "") {
                  // All products mode — split and cache both types
                  const programProducts = value.filter(
                    (p) => p.product_type === PRODUCT_TYPE_PROGRAM,
                  );
                  const courseRunProducts = value.filter(
                    (p) => p.product_type === PRODUCT_TYPE_COURSERUN,
                  );

                  setFieldValue(
                    `productSelectionsByType.${PRODUCT_TYPE_PROGRAM}`,
                    programProducts,
                  );
                  setFieldValue(
                    `productSelectionsByType.${PRODUCT_TYPE_COURSERUN}`,
                    courseRunProducts,
                  );
                } else {
                  // Normal mode — cache only current type
                  setFieldValue(
                    `productSelectionsByType.${values.product_type}`,
                    value,
                  );
                }
              }}
              dropdownHeight={200}
              className="product-picker"
            />
          </div>
          <div>
            <button type="submit" disabled={isSubmitting}>
              Update promo coupon
            </button>
          </div>
        </Form>
      )}
    />
  );
};
