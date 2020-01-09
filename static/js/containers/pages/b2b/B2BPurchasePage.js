// @flow
import React from "react"
import { connect } from "react-redux"
import { compose } from "redux"
import { pathOr } from "ramda"
import qs from "query-string"

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
  ProductDetail
} from "../../../flow/ecommerceTypes"
import B2BExplanation from "../../../components/B2BExplanation"

type Props = {
  checkout: (payload: B2BCheckoutPayload) => Promise<*>,
  products: Array<ProductDetail>,
  requestPending: boolean,
  couponStatus: ?B2BCouponStatusResponse,
  clearCouponStatus: () => void,
  fetchCouponStatus: (payload: B2BCouponStatusPayload) => Promise<*>,
  location: window.location,
  contractNumber: ?string,
  productId: string,
  discountCode: string
}
type State = {
  errors: string | Object | null
}
type Values = {
  // these are form fields so they all start off as strings
  num_seats: string,
  product: string,
  email: string,
  contract_number: string
}
export class B2BPurchasePage extends React.Component<Props, State> {
  onSubmit = async (values: Values, { setErrors, setSubmitting }: Object) => {
    const { products, checkout, couponStatus } = this.props
    const numSeats = parseInt(values.num_seats)
    let product
    if (isNaN(values.product)) {
      product = products.find(
        product => product.latest_version.readable_id === values.product
      )
    } else {
      product = products.find(
        _product => _product.id === parseInt(values.product)
      )
    }
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
        contract_number:    values.contract_number || null
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
      requestPending
    } = this.props

    const params = new URLSearchParams(this.props.location.search)
    const contractNumber = params.get("contract_number")
    const discountCode = params.get("discount_code")
    let productId = params.get("product_id")
    if (productId) {
      // eslint-disable-next-line no-useless-escape
      productId = productId.replace(/\ /g, "+")
    }

    return (
      <React.Fragment>
        <B2BPurchaseForm
          onSubmit={this.onSubmit}
          products={products}
          checkout={checkout}
          couponStatus={couponStatus}
          contractNumber={contractNumber}
          clearCouponStatus={clearCouponStatus}
          fetchCouponStatus={fetchCouponStatus}
          requestPending={requestPending}
          productId={productId}
          discountCode={discountCode}
        />
        <B2BExplanation alreadyPaid={false} />
      </React.Fragment>
    )
  }
}

const mapStateToProps = state => ({
  products:       state.entities.products || [],
  couponStatus:   state.entities.b2b_coupon_status,
  requestPending: pathOr(
    false,
    ["queries", "b2bCheckoutMutation", "isPending"],
    state
  )
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
