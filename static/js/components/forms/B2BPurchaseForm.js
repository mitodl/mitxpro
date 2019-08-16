// @flow
import React from "react"
import { ErrorMessage, Field, Formik, Form } from "formik"
import Decimal from "decimal.js-light"

import B2BPurchaseSummary from "../B2BPurchaseSummary"
import ProductSelector from "../input/ProductSelector"

import type { ProductDetail } from "../../flow/ecommerceTypes"

type Props = {
  products: Array<ProductDetail>,
  onSubmit: Function,
  requestPending: boolean
}

const errorMessageRenderer = msg => <span className="error">{msg}</span>

export const validate = (values: Object) => {
  const errors = {}

  const numSeats = parseInt(values.num_seats)
  if (isNaN(numSeats) || numSeats <= 0) {
    errors.num_seats = "Number of seats is required"
  }

  if (!values.email.includes("@")) {
    errors.email = "Email is required"
  }

  if (!values.product) {
    errors.product = "No product selected"
  }

  return errors
}

const B2BPurchaseForm = ({ onSubmit, products, requestPending }: Props) => (
  <Formik
    onSubmit={onSubmit}
    initialValues={{
      num_seats: "",
      email:     "",
      product:   ""
    }}
    validate={validate}
    render={({ values }) => {
      let itemPrice, totalPrice, numSeats
      const productId = parseInt(values.product)
      const product = products.find(product => product.id === productId)
      const productVersion = product ? product.latest_version : null
      if (productVersion) {
        numSeats = parseInt(values.num_seats)
        if (!isNaN(numSeats) && productVersion.price !== null) {
          itemPrice = new Decimal(productVersion.price)
          totalPrice = itemPrice * new Decimal(numSeats)
        }
      }

      return (
        <Form className="b2b-purchase-form container">
          <div className="row">
            <div className="col-lg-12">
              <div className="title">Bulk Seats</div>
            </div>
          </div>
          <div className="row">
            <div className="col-lg-8">
              <p>Purchase one or more seats for your team.</p>
              <label htmlFor="product">
                <h5>Select to view available courses or programs:</h5>
                <Field
                  component={ProductSelector}
                  products={products}
                  name="product"
                />
                <ErrorMessage name="product" render={errorMessageRenderer} />
              </label>

              <label htmlFor="num_seats">
                *Number of seats:
                <Field type="text" name="num_seats" className="num-seats" />
                <ErrorMessage name="num_seats" render={errorMessageRenderer} />
              </label>

              <label htmlFor="email">
                *Email Address:
                <Field type="text" name="email" />
                <ErrorMessage name="email" render={errorMessageRenderer} />
              </label>
            </div>
            <div className="col-lg-4">
              <B2BPurchaseSummary
                itemPrice={itemPrice}
                totalPrice={totalPrice}
                numSeats={numSeats}
              />

              <button
                className="checkout-button"
                type="submit"
                disabled={requestPending}
              >
                Place order
              </button>
            </div>
          </div>
        </Form>
      )
    }}
  />
)

export default B2BPurchaseForm
