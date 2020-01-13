// @flow
/* global SETTINGS: false */
declare var dataLayer: Object[]

import React from "react"
import DocumentTitle from "react-document-title"
import { CHECKOUT_PAGE_TITLE } from "../../constants"
import { connect } from "react-redux"
import { mutateAsync, requestAsync } from "redux-query"
import { compose } from "redux"
import queryString from "query-string"
import { pathOr } from "ramda"
import * as Sentry from "@sentry/browser"

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
  appliedInitialCoupon: boolean,
  errors: string | Object | null,
  isLoading: boolean,
  showGenericError: boolean
}

export const calcSelectedRunIds = (
  item: BasketItem,
  preselectId: number = 0
): { [number]: number } => {
  if (item.type === "courserun") {
    const course = item.courses[0]
    return {
      [course.id]: item.object_id
    }
  }

  const selectedRunIds = {}
  for (const course of item.courses) {
    if (course.next_run_id) {
      selectedRunIds[course.id] = course.next_run_id
    }
  }

  const courseLookup = {}
  for (const course of item.courses) {
    for (const run of course.courseruns) {
      courseLookup[run.id] = course.id
    }
  }

  // Try to preselect a run if the ID was given
  if (preselectId) {
    const courseId = courseLookup[preselectId]
    selectedRunIds[courseId] = preselectId
  }

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
    errors:               null,
    isLoading:            true,
    showGenericError:     false
  }

  logExceptionToSentry = (
    title: ?string = "General Exception",
    extra: ?Object = {}
  ) => {
    Sentry.withScope(scope => {
      scope.setExtra("extra", extra)
      scope.setFingerprint(["{{ default }}", title])
      Sentry.captureException(new Error(title))
    })
  }

  getQueryParams = () => {
    const {
      location: { search }
    } = this.props
    const params = queryString.parse(search)
    return {
      productId:   params.product,
      preselectId: parseInt(params.preselect),
      couponCode:  params.code
    }
  }

  componentDidMount = async () => {
    const { fetchBasket, updateBasket } = this.props
    const { productId } = this.getQueryParams()
    if (!productId) {
      await fetchBasket()
    } else {
      const basketResponse = await updateBasket({
        items: [{ readable_id: productId }]
      })
      if (basketResponse.status !== 200) {
        if (basketResponse.body && basketResponse.body.errors) {
          this.logExceptionToSentry(
            "Basket API exception",
            basketResponse.body.errors
          )
          this.setState({
            errors: basketResponse.body.errors
          })
        } else {
          this.logExceptionToSentry("Basket API error", basketResponse)
          this.setState({ showGenericError: true })
        }
      } else {
        this.setState({ showGenericError: false })
      }
    }
    this.setState({
      isLoading: false
    })
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
        readable_id: item.readable_id,
        run_ids:     Object.values(values.runs).map(runId => parseInt(runId))
      })),
      coupons:       values.couponCode ? [{ code: values.couponCode }] : [],
      data_consents: values.dataConsent ? [basket.data_consents[0].id] : []
    }
    try {
      const basketResponse = await updateBasket(basketPayload)
      if (basketResponse.status !== 200) {
        if (basketResponse.body && basketResponse.body.errors) {
          this.logExceptionToSentry(
            "Basket API exception",
            basketResponse.body.errors
          )
          actions.setErrors(basketResponse.body.errors)
        } else {
          this.logExceptionToSentry("Basket API error", basketResponse)
          this.setState({ showGenericError: true })
        }
        return
      }

      this.setState({ showGenericError: false })

      const checkoutResponse = await checkout()
      if (checkoutResponse.status !== 200) {
        if (checkoutResponse.body && checkoutResponse.body.errors) {
          this.logExceptionToSentry(
            "Checkout API exception",
            checkoutResponse.body.errors
          )
          actions.setErrors(checkoutResponse.body.errors)
        } else {
          this.logExceptionToSentry("Checkout API error", checkoutResponse)
          this.setState({ showGenericError: true })
        }
        return
      }

      this.setState({ showGenericError: false })

      const { method, url, payload } = checkoutResponse.body
      if (method === "GET") {
        if (SETTINGS.gtmTrackingID) {
          dataLayer.push({
            event:            "purchase",
            transactionId:    payload.transaction_id,
            transactionTotal: payload.transaction_total,
            productType:      payload.product_type,
            coursewareId:     payload.courseware_id,
            referenceNumber:  payload.reference_number,
            eventTimeout:     2000,
            eventCallback:    () => {
              setTimeout(() => {
                window.location = url
              }, 1500)
            }
          })
        } else {
          window.location = url
        }
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
            code: couponCode.trim()
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
    productId: string,
    runId: number,
    setFieldError: SetFieldError
  ) => {
    const { updateBasket } = this.props
    const response = await updateBasket({
      items: [{ readable_id: productId, run_ids: runId ? [runId] : [] }]
    })
    setFieldError(
      "runs",
      response.body.errors ? response.body.errors.runs : undefined
    )
  }

  render() {
    const { basket, requestPending } = this.props
    const { errors, isLoading, showGenericError } = this.state

    const item = basket && basket.items[0]
    if (!basket || !item) {
      return (
        <DocumentTitle title={`${SETTINGS.site_name} | ${CHECKOUT_PAGE_TITLE}`}>
          {isLoading ? (
            <div className="checkout-page  checkout-loader text-center align-self-center">
              <div className="loader-area">
                <img
                  src="/static/images/loader.gif"
                  className="mx-auto d-block"
                />
                One moment while we prepare checkout
              </div>
            </div>
          ) : showGenericError ? (
            <div className="checkout-page">
              <div className="error">
                Something went wrong. Please contact us at{" "}
                <u>
                  <a
                    href="https://xpro.zendesk.com/hc/en-us/requests/new"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    Customer Support
                  </a>
                </u>
                .
              </div>
            </div>
          ) : (
            <div className="checkout-page">
              No item in basket
              {formatErrors(errors)}
            </div>
          )}
        </DocumentTitle>
      )
    }

    const coupon = basket.coupons.find(coupon =>
      coupon.targets.includes(item.id)
    )
    const { couponCode, preselectId } = this.getQueryParams()
    const selectedRuns = calcSelectedRunIds(item, preselectId)

    return (
      <DocumentTitle title={`${SETTINGS.site_name} | ${CHECKOUT_PAGE_TITLE}`}>
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
      </DocumentTitle>
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
