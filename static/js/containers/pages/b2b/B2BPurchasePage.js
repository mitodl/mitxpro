// @flow
import React from "react"
import { connect } from "react-redux"
import { compose } from "redux"
import { pathOr } from "ramda"
import { connectRequest, mutateAsync } from "redux-query"

import B2BPurchaseForm from "../../../components/forms/B2BPurchaseForm"

import { createCyberSourceForm } from "../../../lib/form"
import queries from "../../../lib/queries"

import type {
  BulkCheckoutPayload,
  ProductDetail
} from "../../../flow/ecommerceTypes"

type Props = {
  checkout: (payload: BulkCheckoutPayload) => Promise<*>,
  products: Array<ProductDetail>,
  requestPending: boolean
}
type State = {
  errors: string | Object | null
}
type Values = {
  // these are form fields so they all start off as strings
  num_seats: string,
  product: string,
  email: string
}
export class B2BPurchasePage extends React.Component<Props, State> {
  onSubmit = async (values: Values, { setErrors, setSubmitting }: Object) => {
    const { products, checkout } = this.props
    const numSeats = parseInt(values.num_seats)
    const product = products.find(
      _product => _product.id === parseInt(values.product)
    )
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
        product_version_id: productVersion.id
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
    const { checkout, products, requestPending } = this.props

    return (
      <B2BPurchaseForm
        onSubmit={this.onSubmit}
        products={products}
        checkout={checkout}
        requestPending={requestPending}
      />
    )
  }
}

const mapStateToProps = state => ({
  products:       state.entities.products || [],
  requestPending: pathOr(
    false,
    ["queries", "b2bCheckoutMutation", "isPending"],
    state
  )
})
const mapDispatchToProps = dispatch => ({
  checkout: (payload: BulkCheckoutPayload) =>
    dispatch(mutateAsync(queries.ecommerce.b2bCheckoutMutation(payload)))
})

const mapPropsToConfig = () => [queries.ecommerce.productsQuery()]

export default compose(
  connect(
    mapStateToProps,
    mapDispatchToProps
  ),
  connectRequest(mapPropsToConfig)
)(B2BPurchasePage)
