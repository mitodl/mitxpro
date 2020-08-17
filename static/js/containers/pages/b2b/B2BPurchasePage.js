// @flow
import React from "react"
import { connect } from "react-redux"
import { compose } from "redux"
import { pathOr } from "ramda"
import { createStructuredSelector } from "reselect"

import {
  connectRequest,
  mutateAsync,
  requestAsync,
  updateEntities
} from "redux-query"

import B2BPurchaseForm from "../../../components/forms/B2BPurchaseForm"

import { createCyberSourceForm } from "../../../lib/form"
import queries from "../../../lib/queries"

import type {
  B2BCheckoutPayload,
  B2BCouponStatusPayload,
  B2BCouponStatusResponse,
  Product
} from "../../../flow/ecommerceTypes"
import { findProductById } from "../../../lib/ecommerce"

type Props = {
  checkout: (payload: B2BCheckoutPayload) => Promise<*>,
  products: Array<Product>,
  requestPending: boolean,
  couponStatus: ?B2BCouponStatusResponse,
  clearCouponStatus: () => void,
  fetchCouponStatus: (payload: B2BCouponStatusPayload) => Promise<*>,
  location: window.location,
  contractNumber: ?string,
  productId: string,
  discountCode: string,
  isLoading: boolean
}
type State = {
  errors: string | Object | null
}
type Values = {
  // these are form fields so they all start off as strings
  num_seats: string,
  product: Object,
  email: string,
  contract_number: string
}
export class B2BPurchasePage extends React.Component<Props, State> {
  onSubmit = async (values: Values, { setErrors, setSubmitting }: Object) => {
    const { products, checkout, couponStatus } = this.props
    const numSeats = parseInt(values.num_seats)
    const { productId, programRunId } = values.product
    const product = findProductById(products, productId)
    if (!product) {
      throw new Error(
        "No product found. This should have been caught in validation."
      )
    }

    const productVersion = product.latest_version

    try {
      const checkoutResponse = await checkout({
        num_seats:          numSeats,
        email:              values.email,
        product_version_id: productVersion.id,
        discount_code:      couponStatus ? couponStatus.code : null,
        contract_number:    values.contract_number || null,
        run_id:             programRunId
      })

      if (checkoutResponse.status !== 200) {
        if (checkoutResponse.body.errors) {
          setErrors(checkoutResponse.body.errors)
        }
        return
      }

      const { method, url, payload } = checkoutResponse.body
      if (method === "GET") {
        window.location = url
      } else {
        const form = createCyberSourceForm(url, payload)
        const body: HTMLElement = (document.querySelector("body"): any)
        body.appendChild(form)
        form.submit()
      }
    } finally {
      setSubmitting(false)
    }
  }

  render() {
    const {
      checkout,
      clearCouponStatus,
      couponStatus,
      fetchCouponStatus,
      products,
      requestPending,
      isLoading
    } = this.props

    const params = new URLSearchParams(this.props.location.search)
    const contractNumber = params.get("contract_number")
    const discountCode = params.get("code")
    const seats = params.get("seats")
    let productId = params.get("product_id")
    if (productId && isNaN(productId)) {
      // eslint-disable-next-line no-useless-escape
      productId = productId.replace(/\ /g, "+")
    }

    return (
      <React.Fragment>
        {isLoading ? (
          <div className="page page-loader text-center align-self-center">
            <div className="loader-area">
              <img
                src="/static/images/loader.gif"
                className="mx-auto d-block"
              />
              One moment while we prepare bulk purchase page
            </div>
          </div>
        ) : (
          <B2BPurchaseForm
            onSubmit={this.onSubmit}
            products={products.filter(
              product => product.visible_in_bulk_form === true
            )}
            checkout={checkout}
            couponStatus={couponStatus}
            contractNumber={contractNumber}
            clearCouponStatus={clearCouponStatus}
            fetchCouponStatus={fetchCouponStatus}
            requestPending={requestPending}
            productId={productId}
            discountCode={discountCode}
            seats={seats}
          />
        )}
      </React.Fragment>
    )
  }
}

const mapStateToProps = state =>
  createStructuredSelector({
    products:       queries.ecommerce.productsSelector,
    couponStatus:   queries.ecommerce.b2bCouponStatusSelector,
    requestPending: pathOr(false, [
      "queries",
      "b2bCheckoutMutation",
      "isPending"
    ]),
    isLoading: pathOr(true, ["queries", "products", "isPending"])
  })
const mapDispatchToProps = dispatch => ({
  checkout: (payload: B2BCheckoutPayload) =>
    dispatch(mutateAsync(queries.ecommerce.b2bCheckoutMutation(payload))),
  clearCouponStatus: () =>
    dispatch(
      updateEntities({
        b2b_coupon_status: () => null
      })
    ),
  fetchCouponStatus: (payload: B2BCouponStatusPayload) =>
    dispatch(requestAsync(queries.ecommerce.b2bCouponStatus(payload)))
})

const mapPropsToConfig = () => [queries.ecommerce.productsQuery()]

export default compose(
  connect(
    mapStateToProps,
    mapDispatchToProps
  ),
  connectRequest(mapPropsToConfig)
)(B2BPurchasePage)
