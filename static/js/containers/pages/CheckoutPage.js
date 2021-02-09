// @flow
/* global SETTINGS: false */

declare var dataLayer: Object[]

import React from "react"
import { RouteComponentProps } from "react-router-dom"
import DocumentTitle from "react-document-title"
import { CHECKOUT_PAGE_TITLE } from "../../constants"
import { connect } from "react-redux"
import { mutateAsync, requestAsync } from "redux-query"
import { compose } from "redux"
import queryString from "query-string"
import { pathOr } from "ramda"

import {
  CheckoutForm,
  renderGenericError
} from "../../components/forms/CheckoutForm"

import queries from "../../lib/queries"
import { createCyberSourceForm, formatErrors } from "../../lib/form"
import { calcSelectedRunIds } from "../../lib/ecommerce"
import { generateLoginRedirectUrl } from "../../lib/auth"
import {
  getErrorMessages,
  isErrorResponse,
  isSuccessResponse,
  isUnauthorizedResponse
} from "../../lib/util"

import type { Response } from "redux-query"
import type {
  BasketResponse,
  BasketPayload,
  CheckoutResponse,
  BasketItem,
  CheckoutPayload
} from "../../flow/ecommerceTypes"
import type { HttpRespErrorMessage, HttpResponse } from "../../flow/httpTypes"
import type {
  Actions,
  SetFieldError,
  Values
} from "../../components/forms/CheckoutForm"

type Props = RouteComponentProps & {
  basket: ?BasketResponse,
  requestPending: boolean,
  checkout: () => Promise<Response<CheckoutResponse>>,
  fetchBasket: () => Promise<*>,
  updateBasket: (payload: BasketPayload) => Promise<*>
}
type State = {
  appliedInitialCoupon: boolean,
  loadingFailed: boolean,
  loadingErrorMessages: string | Object | null,
  isLoading: boolean,
  isSubmitting: boolean,
  isLoggedOut: boolean,
  basketProduct: string
}

export class CheckoutPage extends React.Component<Props, State> {
  state = {
    appliedInitialCoupon: false,
    loadingFailed:        false,
    loadingErrorMessages: null,
    isLoading:            true,
    isSubmitting:         false,
    isLoggedOut:          false,
    basketProduct:        ""
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
      this.setState({
        isLoading: false
      })
      return
    }

    const basketResponse = await updateBasket({
      items: [{ product_id: productId }]
    })
    if (isSuccessResponse(basketResponse)) {
      if (basketResponse.body && basketResponse.body.items) {
        this.trackAddToCartEvent(basketResponse.body.items)
      }
      this.setState({
        isLoading:     false,
        loadingFailed: false,
        basketProduct: productId
      })
    } else {
      const errors = this.getErrorsOrRedirect(basketResponse)
      if (isUnauthorizedResponse(basketResponse)) {
        return
      }
      this.setState({
        isLoading:            false,
        loadingFailed:        true,
        loadingErrorMessages: errors
      })
    }
  }

  componentDidUpdate() {
    const { isLoggedOut, isLoading, isSubmitting } = this.state
    const { history } = this.props
    if (isLoggedOut && !isLoading && !isSubmitting) {
      // Using history.push instead of <Redirect /> due to testing difficulties
      history.push(generateLoginRedirectUrl())
    }
  }

  trackAddToCartEvent = (items: Array<BasketItem>) => {
    if (SETTINGS.gtmTrackingID) {
      dataLayer.push({
        event:          "addToCart",
        "course-id":    items[0].readable_id,
        "course-price": items[0].price || "0"
      })
    }
  }

  trackSubmitEvent = (url: string, payload: CheckoutPayload) => {
    if (SETTINGS.gtmTrackingID) {
      dataLayer.push({
        event:            "purchase",
        transactionId:    payload.transaction_id || null,
        transactionTotal: payload.transaction_total || null,
        productType:      payload.product_type || null,
        coursewareId:     payload.courseware_id || null,
        referenceNumber:  payload.reference_number,
        eventTimeout:     2000,
        eventCallback:    () => {
          setTimeout(() => {
            window.location = url
          }, 1500)
        }
      })
    }
  }

  getErrorsOrRedirect = (
    errorResponse: HttpResponse
  ): ?HttpRespErrorMessage => {
    if (isUnauthorizedResponse(errorResponse)) {
      this.setState({ isLoggedOut: true, isLoading: false })
      return
    }
    return getErrorMessages(errorResponse)
  }

  submit = async (values: Values, actions: Actions) => {
    const { basket, updateBasket, checkout, history } = this.props
    const { basketProduct } = this.state

    if (!basket) {
      // if there is no basket there shouldn't be any submit button rendered
      throw new Error("Expected basket to exist")
    }
    this.setState({ isSubmitting: true })

    // update basket with selected runs
    const basketPayload = {
      items: basket.items.map(item => ({
        product_id: basketProduct,
        run_ids:    Object.values(values.runs).map(runId => parseInt(runId))
      })),
      coupons:       values.couponCode ? [{ code: values.couponCode }] : [],
      data_consents: values.dataConsent ? [basket.data_consents[0].id] : []
    }
    try {
      const basketResponse = await updateBasket(basketPayload)
      if (isErrorResponse(basketResponse)) {
        const basketErrors = this.getErrorsOrRedirect(basketResponse)
        if (isUnauthorizedResponse(basketResponse)) {
          return
        }
        actions.setErrors(
          basketErrors || {
            genericBasket: true
          }
        )
        return
      }

      const checkoutResponse = await checkout()
      if (isErrorResponse(checkoutResponse)) {
        const checkoutErrors = this.getErrorsOrRedirect(checkoutResponse)
        if (isUnauthorizedResponse(checkoutResponse)) {
          return
        }
        actions.setErrors(
          checkoutErrors || {
            genericSubmit: true
          }
        )
        return
      }

      const { method, url, payload } = checkoutResponse.body
      if (method === "GET") {
        if (SETTINGS.gtmTrackingID) {
          this.trackSubmitEvent(url, payload)
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
      this.setState({ isSubmitting: false })
    }
  }

  submitCoupon = async (couponCode: ?string, setFieldError: SetFieldError) => {
    const { updateBasket, history } = this.props
    const response = await updateBasket({
      coupons: couponCode
        ? [
          {
            code: couponCode.trim()
          }
        ]
        : []
    })
    if (isSuccessResponse(response)) {
      setFieldError("coupons", null)
    } else {
      const errors = this.getErrorsOrRedirect(response)
      if (isUnauthorizedResponse(response)) {
        return
      }
      if (errors && errors.coupons) {
        setFieldError("coupons", errors.coupons)
      } else {
        setFieldError("genericBasket", true)
      }
    }
  }

  updateProduct = async (
    productId: number | string,
    runId: number,
    setFieldError: SetFieldError
  ) => {
    const { updateBasket, history } = this.props
    const response = await updateBasket({
      items: [{ product_id: productId, run_ids: runId ? [runId] : [] }]
    })
    if (isSuccessResponse(response)) {
      setFieldError("runs", "")
    } else {
      const errors = this.getErrorsOrRedirect(response)
      if (isUnauthorizedResponse(response)) {
        return
      }
      if (errors && errors.runs) {
        setFieldError("runs", errors.runs)
      } else {
        setFieldError("genericBasket", true)
      }
    }
    this.setState({ basketProduct: productId.toString() })
  }

  renderLoading = () => {
    return (
      <div className="checkout-page page-loader text-center align-self-center">
        <div className="loader-area">
          <img
            src="/static/images/loader.gif"
            className="mx-auto d-block"
            alt="Loading..."
          />
          One moment while we prepare checkout
        </div>
      </div>
    )
  }

  renderLoadingError = () => {
    const { loadingFailed, loadingErrorMessages } = this.state
    return (
      <div className="checkout-page">
        {!loadingFailed || loadingErrorMessages ? (
          <React.Fragment>
            No item in basket
            {formatErrors(loadingErrorMessages)}
          </React.Fragment>
        ) : (
          renderGenericError()
        )}
      </div>
    )
  }

  render() {
    const { basket, requestPending } = this.props
    const { isLoading } = this.state

    let pageBody
    const item = basket && basket.items[0]

    if (isLoading) {
      pageBody = this.renderLoading()
    } else if (!basket || !item) {
      pageBody = this.renderLoadingError()
    } else {
      const coupon = basket.coupons.find(coupon =>
        coupon.targets.includes(item.id)
      )
      const { couponCode, preselectId } = this.getQueryParams()
      const selectedRuns = calcSelectedRunIds(item, preselectId)
      pageBody = (
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
    return (
      <DocumentTitle title={`${SETTINGS.site_name} | ${CHECKOUT_PAGE_TITLE}`}>
        {pageBody}
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
  updateBasket: (payload: BasketPayload) =>
    dispatch(mutateAsync(queries.ecommerce.basketMutation(payload)))
})

export default compose(
  connect(
    mapStateToProps,
    mapDispatchToProps
  )
)(CheckoutPage)
