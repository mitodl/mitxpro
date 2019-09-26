// @flow
import React from "react"
import * as R from "ramda"
import { Formik, Field, Form } from "formik"
import * as yup from "yup"

import { RadioButtonGroup, RadioButton } from "../input/radio"
import { PRODUCT_TYPE_COURSERUN, PRODUCT_TYPE_LABELS } from "../../constants"
import { parseIntOrUndefined } from "../../lib/util"

import type {
  BulkCouponPayment,
  BulkCouponSendResponse,
  ProductMap
} from "../../flow/ecommerceTypes"

const getFirstId = R.compose(
  R.prop("id"),
  R.head
)

const getFirstKeyAsInt = R.compose(
  parseIntOrUndefined,
  R.head,
  R.keys
)

const bulkEnrollmentValidations = yup.object().shape({
  users_file:        yup.mixed().required("User CSV file is required"),
  product_id:        yup.number().required("Product selection is required"),
  coupon_payment_id: yup.number().required("Coupon selection is required")
})

type BulkEnrollmentFormProps = {
  bulkCouponPayments: Array<BulkCouponPayment>,
  productMap: ProductMap,
  submitRequest: Function
}

type BulkEnrollmentFormState = {
  successResponseData: ?BulkCouponSendResponse
}

export class BulkEnrollmentForm extends React.Component<
  BulkEnrollmentFormProps,
  BulkEnrollmentFormState
> {
  fileInput: Object

  state = {
    successResponseData: null
  }

  constructor(props: BulkEnrollmentFormProps) {
    super(props)
    this.fileInput = React.createRef()
  }

  getBulkCouponsForProduct = (productId: number): Array<BulkCouponPayment> => {
    const { bulkCouponPayments } = this.props

    return bulkCouponPayments.filter(bulkCoupon => {
      return bulkCoupon.products.find(product => product.id === productId)
    })
  }

  onChangeProductType = R.curry((setFieldValue: Function, e: Object) => {
    const { productMap } = this.props

    const selectedProductType = e.target.value
    const selectedProductId = getFirstKeyAsInt(productMap[selectedProductType])
    setFieldValue("product_type", selectedProductType)
    setFieldValue("product_id", selectedProductId)
    setFieldValue(
      "coupon_payment_id",
      getFirstId(this.getBulkCouponsForProduct(selectedProductId))
    )
  })

  onChangeProductId = R.curry((setFieldValue: Function, e: Object) => {
    const selectedProductId = parseInt(e.target.value)
    setFieldValue("product_id", selectedProductId)
    setFieldValue(
      "coupon_payment_id",
      getFirstId(this.getBulkCouponsForProduct(selectedProductId))
    )
  })

  onSubmit = async (
    payload: Object,
    { setSubmitting, setErrors, resetForm }: Object
  ) => {
    const { submitRequest } = this.props
    try {
      const result = await submitRequest(payload)
      if (result && result.status === 200) {
        resetForm()
        this.fileInput.value = ""
        this.setState({ successResponseData: result.body })
      } else {
        const errors = R.path(["body", "errors"], result)
        if (errors) {
          setErrors(R.mergeAll(errors))
        }
        this.setState({ successResponseData: null })
      }
    } finally {
      setSubmitting(false)
    }
  }

  render() {
    const { successResponseData } = this.state
    const { productMap } = this.props

    const initialProductType = PRODUCT_TYPE_COURSERUN
    const initialProductId = getFirstKeyAsInt(productMap[initialProductType])
    const initialCouponPaymentId = getFirstId(
      this.getBulkCouponsForProduct(initialProductId)
    )

    return (
      <Formik
        onSubmit={this.onSubmit}
        validationSchema={bulkEnrollmentValidations}
        initialValues={{
          users_file:        "",
          product_type:      initialProductType,
          product_id:        initialProductId,
          coupon_payment_id: initialCouponPaymentId
        }}
        render={({ values, isSubmitting, errors, touched, setFieldValue }) => (
          <Form className="bulk-enrollment-form">
            <section>
              <label htmlFor="users_file">User CSV: </label>
              <input
                type="file"
                id="users_file"
                name="users_file"
                accept=".csv"
                onChange={event => {
                  setFieldValue("users_file", event.target.files[0])
                }}
                ref={ref => (this.fileInput = ref)}
              />
              {errors.users_file && (
                <div className="error">{errors.users_file}</div>
              )}
            </section>

            <section>
              <div>Product type:</div>
              <RadioButtonGroup>
                {Object.keys(PRODUCT_TYPE_LABELS).map(productType => (
                  <Field
                    key={productType}
                    component={RadioButton}
                    name="product_type"
                    id={productType}
                    label={PRODUCT_TYPE_LABELS[productType]}
                    onChange={this.onChangeProductType(setFieldValue)}
                  />
                ))}
              </RadioButtonGroup>
            </section>

            <section>
              <label htmlFor="product_id">
                {PRODUCT_TYPE_LABELS[values.product_type]}:
              </label>
              <Field
                component="select"
                name="product_id"
                onChange={this.onChangeProductId(setFieldValue)}
              >
                {R.toPairs(productMap[values.product_type]).map(([productId, productObject]) => (
                  <option key={productId} value={productId}>
                    {productObject.title}
                  </option>
                ))}
              </Field>
            </section>

            {values.product_id && (
              <React.Fragment>
                <section>
                  <label htmlFor="coupon_payment_id">Coupon: </label>
                  <Field component="select" name="coupon_payment_id">
                    {this.getBulkCouponsForProduct(values.product_id).map(
                      (couponPayment, i) => (
                        <option key={i} value={couponPayment.id}>
                          {couponPayment.name} (
                          {couponPayment.version.num_coupon_codes} codes)
                        </option>
                      )
                    )}
                  </Field>
                </section>
                <section>
                  <button type="submit" disabled={isSubmitting}>
                    Enroll Learners
                  </button>
                </section>
              </React.Fragment>
            )}

            {successResponseData && R.isEmpty(touched) && (
              <div className="success">
                Success! Enrollment emails sent to{" "}
                {successResponseData.emails.length} users.
              </div>
            )}
          </Form>
        )}
      />
    )
  }
}
