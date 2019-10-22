// @flow
import React from "react"
import * as R from "ramda"
import { Formik, Field, Form } from "formik"
import * as yup from "yup"

import { RadioButtonGroup, RadioButton } from "../input/radio"
import { PRODUCT_TYPE_COURSERUN, PRODUCT_TYPE_LABELS } from "../../constants"
import { parseIntOrUndefined } from "../../lib/util"
import { bulkAssignmentCsvUrl, bulkReceiptCsvUrl } from "../../lib/urls"

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
  successResponseData: ?BulkCouponSendResponse,
  productType: string
}

export class BulkEnrollmentForm extends React.Component<
  BulkEnrollmentFormProps,
  BulkEnrollmentFormState
> {
  fileInput: Object

  state = {
    successResponseData: null,
    productType:         PRODUCT_TYPE_COURSERUN
  }

  constructor(props: BulkEnrollmentFormProps) {
    super(props)
    this.fileInput = React.createRef()
    this.getSortedIds.bind(true)
  }

  getBulkCouponsForProduct = (
    productId: number | string
  ): Array<BulkCouponPayment> => {
    const { bulkCouponPayments } = this.props
    return bulkCouponPayments.filter(bulkCoupon => {
      return bulkCoupon.products.find(
        product => parseInt(product.id) === parseInt(productId)
      )
    })
  }

  onChangeProductType = R.curry((setFieldValue: Function, e: Object) => {
    const { productMap } = this.props

    const selectedProductType = e.target.value
    const selectedProductId = this.getSortedIds(
      productMap,
      selectedProductType
    )[0]
    setFieldValue("product_type", selectedProductType)
    setFieldValue("product_id", selectedProductId)
    setFieldValue(
      "coupon_payment_id",
      getFirstId(this.getBulkCouponsForProduct(selectedProductId))
    )
    this.setState({
      productType: selectedProductType
    })
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

  getSortedIds = (productMap: ProductMap, initialProductType: string) => {
    const sortedIds: Array<string> = Object.keys(
      productMap[initialProductType]
    ).sort((key1, key2) => {
      const sortKey =
        initialProductType === PRODUCT_TYPE_COURSERUN
          ? "courseware_id"
          : "readable_id"
      if (
        productMap[initialProductType][key1][sortKey] <
        productMap[initialProductType][key2][sortKey]
      ) {
        return -1
      } else if (
        productMap[initialProductType][key1][sortKey] >
        productMap[initialProductType][key2][sortKey]
      ) {
        return 1
      }
      return 0
    })
    return sortedIds
  }

  render() {
    const { successResponseData } = this.state
    const { productMap } = this.props

    const initialProductType = this.state.productType

    const sortedProductIds = this.getSortedIds(productMap, initialProductType)

    const initialProductId = parseInt(sortedProductIds[0])
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
                {sortedProductIds.map(productId => (
                  <option key={productId} value={productId}>
                    {values.product_type === "program"
                      ? productMap[values.product_type][productId][
                        "readable_id"
                      ]
                      : productMap[values.product_type][productId][
                        "courseware_id"
                      ]}
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
                <p>
                  Success! Enrollment emails sent to{" "}
                  {successResponseData.emails.length} users.
                </p>
                <p>
                  <a
                    href={bulkAssignmentCsvUrl(
                      successResponseData.bulk_assignment_id
                    )}
                  >
                    Download CSV of coupon assignments{" "}
                    <i className="material-icons">save_alt</i>
                  </a>
                </p>
              </div>
            )}
          </Form>
        )}
      />
    )
  }
}
