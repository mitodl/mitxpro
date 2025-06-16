// @flow
import React from "react";
import moment from "moment";
import { Picky } from "react-picky";
import { filter, pathSatisfies, equals, always, sortBy, prop } from "ramda";
import FormikDatePicker from "../input/FormikDatePicker";
import { Formik, Field, Form, ErrorMessage } from "formik";
import * as yup from "yup";

import { PRODUCT_TYPE_COURSERUN, PRODUCT_TYPE_PROGRAM } from "../../constants";
import { zeroHour, finalHour, getProductSelectLabel } from "../../lib/util";
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
    .when("activation_date", (activationDate, schema) => {
      let minDate;
      if (!activationDate || isNaN(new Date(activationDate))) {
        minDate = new Date();
      } else {
        const today = new Date();
        const activation = new Date(activationDate);
        minDate = today > activation ? today : activation;
      }
      return schema.min(
        minDate,
        "Expiration date must be after today/activation date",
      );
    })
    .required("Valid expiration date required"),
  products: yup.array().when("is_global", {
    is: false,
    then: (schema) => schema.min(1, "${min} or more products must be selected"),
  }),
  is_global: yup.boolean(),
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
        is_global: false,
      }}
      render={({
        isSubmitting,
        setFieldValue,
        setFieldTouched,
        errors,
        touched,
        values,
        resetForm,
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
                  if (!selectedId) {
                    // Reset form to initial values
                    resetForm();
                    return;
                  }
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
                    setFieldValue("is_global", selectedCoupon.is_global);

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
              <FormikDatePicker
                name="activation_date"
                label="Valid from*"
                values={values}
                setFieldValue={setFieldValue}
                setFieldTouched={setFieldTouched}
              />
            </div>
            <div className="block">
              <FormikDatePicker
                name="expiration_date"
                label="Valid until*"
                values={values}
                setFieldValue={setFieldValue}
                setFieldTouched={setFieldTouched}
              />
            </div>
          </div>
          <div
            className={values.include_future_runs ? "flex disabled" : "flex"}
          >
            <label htmlFor="is_global">
              <Field
                type="checkbox"
                name="is_global"
                checked={values.is_global}
                onChange={() => {
                  values.is_global = !values.is_global;
                  setFieldValue("is_global", values.is_global);
                  if (values.is_global) {
                    setFieldValue("products", []);
                    setFieldTouched("products");
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
          {values.product_type !== "" && (
            <p className="small-text warning">
              {" "}
              Switch to All Products to select both course runs and
              programs.{" "}
            </p>
          )}
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
