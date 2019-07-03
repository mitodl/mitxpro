// @flow
import React from "react"
import { connect } from "react-redux"
import { mutateAsync, requestAsync } from "redux-query"
import { compose } from "redux"
import queryString from "query-string"
import { pathOr } from "ramda"

import { CheckoutForm } from "../../components/forms/CheckoutForm"

import queries from "../../lib/queries"
import { createCyberSourceForm, formatErrors } from "../../lib/form"

import type { Response } from "redux-query"
import type { Location } from "react-router"
import type {
  BasketResponse,
  BasketPayload,
  CheckoutResponse,
  BasketItem
} from "../../flow/ecommerceTypes"
import type {
  Actions,
  SetFieldError,
  Values
} from "../../components/forms/CheckoutForm"

type Props = {
  basket: ?BasketResponse,
  requestPending: boolean,
  checkout: () => Promise<Response<CheckoutResponse>>,
  fetchBasket: () => Promise<*>,
  location: Location,
  updateBasket: (payload: BasketPayload) => Promise<*>
}
type State = {
  appliedInitialCoupon: false,
  errors: null
}

export const calcSelectedRunIds = (item: BasketItem): { [number]: number } => {
  if (item.type === "courserun") {
    const course = item.courses[0]
    return {
      [course.id]: item.object_id
    }
  }

  const courseLookup = {}
  for (const course of item.courses) {
    for (const run of course.courseruns) {
      courseLookup[run.id] = course.id
    }
  }

  const selectedRunIds = {}
  for (const runId of item.run_ids) {
    const courseId = courseLookup[runId]

    // there should only be one run selected for a course
    selectedRunIds[courseId] = runId
  }
  return selectedRunIds
}

export class CheckoutPage extends React.Component<Props, State> {
  state = {
    appliedInitialCoupon: false,
    errors:               null
  }

  getQueryParams = () => {
    const {
      location: { search }
    } = this.props
    const params = queryString.parse(search)
    return {
      productId:  parseInt(params.product),
      couponCode: params.code
    }
  }

  componentDidMount = async () => {
    const { fetchBasket, updateBasket } = this.props
    const { productId } = this.getQueryParams()
    if (!productId) {
      await fetchBasket()
      return
    }

    const basketResponse = await updateBasket({
      items: [{ product_id: productId }]
    })
    if (basketResponse.status !== 200) {
      if (basketResponse.body.errors) {
        this.setState({
          errors: basketResponse.body.errors
        })
      }
    }
  }

  submit = async (values: Values, actions: Actions) => {
    const { basket, updateBasket, checkout } = this.props

    if (!basket) {
      // if there is no basket there shouldn't be any submit button rendered
      throw new Error("Expected basket to exist")
    }

    // update basket with selected runs
    const basketPayload = {
      items: basket.items.map(item => ({
        product_id: item.product_id,
        // $FlowFixMe: flow doesn't understand that Object.values will return an array of number here
        run_ids:    Object.values(values.runs).map(runId => parseInt(runId))
      })),
      coupons:       values.couponCode ? [{ code: values.couponCode }] : [],
      data_consents: values.dataConsent ? [basket.data_consents[0].id] : []
    }
    try {
      const basketResponse = await updateBasket(basketPayload)
      if (basketResponse.status !== 200) {
        if (basketResponse.body.errors) {
          actions.setErrors(basketResponse.body.errors)
        }
        return
      }

      const checkoutResponse = await checkout()
      if (checkoutResponse.status !== 200) {
        if (checkoutResponse.body.errors) {
          actions.setErrors(checkoutResponse.body.errors)
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
      actions.setSubmitting(false)
    }
  }

  submitCoupon = async (couponCode: ?string, setFieldError: SetFieldError) => {
    const { updateBasket } = this.props
    const response = await updateBasket({
      coupons: couponCode
        ? [
          {
            code: couponCode
          }
        ]
        : []
    })
    setFieldError(
      "coupons",
      response.body.errors ? response.body.errors.coupons : undefined
    )
  }

  updateProduct = async (
    productId: number,
    runId: number,
    setFieldError: SetFieldError
  ) => {
    const { updateBasket } = this.props
    const response = await updateBasket({
      items: [{ product_id: productId, run_ids: runId ? [runId] : [] }]
    })
    setFieldError(
      "runs",
      response.body.errors ? response.body.errors.runs : undefined
    )
  }

  render() {
    const { basket, requestPending } = this.props
    const { errors } = this.state

    const item = basket && basket.items[0]
    if (!basket || !item) {
      return (
        <div className="checkout-page">
          No item in basket
          {formatErrors(errors)}
        </div>
      )
    }

    const coupon = basket.coupons.find(coupon =>
      coupon.targets.includes(item.id)
    )
    const { couponCode } = this.getQueryParams()
    const selectedRuns = calcSelectedRunIds(item)

    return (
      <CheckoutForm
        item={item}
        basket={basket}
        coupon={coupon}
        couponCode={couponCode}
        selectedRuns={selectedRuns}
        submitCoupon={this.submitCoupon}
        onSubmit={this.submit}
        updateProduct={this.updateProduct}
        requestPending={requestPending}
      />
    )
  }
}

const mapStateToProps = state => ({
  basket:         state.entities.basket,
  requestPending:
    pathOr(false, ["queries", "basketMutation", "isPending"], state) ||
    pathOr(false, ["queries", "couponsMutation", "isPending"], state) ||
    pathOr(false, ["queries", "checkoutMutation", "isPending"], state)
})
const mapDispatchToProps = dispatch => ({
  checkout:     () => dispatch(mutateAsync(queries.ecommerce.checkoutMutation())),
  fetchBasket:  () => dispatch(requestAsync(queries.ecommerce.basketQuery())),
  updateBasket: payload =>
    dispatch(mutateAsync(queries.ecommerce.basketMutation(payload)))
})

export default compose(
  connect(
    mapStateToProps,
    mapDispatchToProps
  )
)(CheckoutPage)
