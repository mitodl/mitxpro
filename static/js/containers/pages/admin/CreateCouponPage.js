// @flow
/* global SETTINGS: false */
import React from "react"
import DocumentTitle from "react-document-title"
import { CREATE_COUPON_PAGE_TITLE } from "../../../constants"
import { mergeAll } from "ramda"
import { connectRequest, mutateAsync } from "redux-query"
import { compose } from "redux"
import { connect } from "react-redux"
import { Link } from "react-router-dom"

import { CouponForm } from "../../../components/forms/CouponForm"
import queries from "../../../lib/queries"
import { routes } from "../../../lib/urls"

import type { Response } from "redux-query"
import type {
  Company,
  CouponPaymentVersion,
  Product
} from "../../../flow/ecommerceTypes"
import { createStructuredSelector } from "reselect"
import { COUPON_TYPE_SINGLE_USE } from "../../../constants"

type State = {
  couponId: ?string
}

type StateProps = {|
  products: Array<Product>,
  companies: Array<Company>,
  coupons: Map<string, CouponPaymentVersion>
|}

type DispatchProps = {|
  createCoupon: (coupon: Object) => Promise<Response<CouponPaymentVersion>>
|}

type Props = {|
  ...StateProps,
  ...DispatchProps
|}

export class CreateCouponPage extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = {
      couponId: null
    }
  }

  onSubmit = async (
    couponData: Object,
    { setSubmitting, setErrors }: Object
  ) => {
    const { createCoupon } = this.props
    couponData.product_ids = couponData.products.map(product => product.id)
    if (couponData.coupon_type === COUPON_TYPE_SINGLE_USE) {
      couponData.max_redemptions = 1
    } else {
      couponData.num_coupon_codes = 1
    }
    couponData.amount = couponData.discount / 100
    try {
      const result = await createCoupon(couponData)
      if (result.body && result.body.id) {
        this.setState({ couponId: result.body.id })
      } else if (result.body && result.body.errors) {
        setErrors(mergeAll(result.body.errors))
      }
    } finally {
      setSubmitting(false)
    }
  }

  clearSuccess = async () => {
    await this.setState({ couponId: null })
  }

  render() {
    const { couponId } = this.state
    const { coupons, companies, products } = this.props
    // $FlowFixMe: flow doesn't like coupons[couponId] but it works fine
    const newCoupon = coupons && couponId ? coupons[couponId] : null
    return (
      <DocumentTitle
        title={`${SETTINGS.site_name} | ${CREATE_COUPON_PAGE_TITLE}`}
      >
        <div className="ecommerce-admin-body">
          <p>
            <Link to={routes.ecommerceAdmin.index}>
              Back to Ecommerce Admin
            </Link>
          </p>
          <h3>Create a Coupon</h3>
          {newCoupon ? (
            <div className="coupon-success-div">
              {newCoupon.coupon_type === "promo" ? (
                <span>{`Coupon "${
                  newCoupon.payment.name
                }" successfully created.`}</span>
              ) : (
                // $FlowFixMe: couponId will never be null here
                <a href={`/couponcodes/${couponId}`}>
                  {`Download coupon codes for "${newCoupon.payment.name}"`}
                </a>
              )}
              <div>
                <input
                  type="button"
                  value="Generate another coupon"
                  onClick={this.clearSuccess}
                />
              </div>
            </div>
          ) : (
            <CouponForm
              onSubmit={this.onSubmit}
              products={products}
              companies={companies}
            />
          )}
        </div>
      </DocumentTitle>
    )
  }
}

const createCoupon = (coupon: Object) =>
  mutateAsync(queries.ecommerce.couponsMutation(coupon))

const mapPropsToConfig = () => [
  queries.ecommerce.productsQuery(),
  queries.ecommerce.companiesQuery()
]

const mapStateToProps = createStructuredSelector({
  products:  queries.ecommerce.productsSelector,
  companies: queries.ecommerce.companiesSelector,
  coupons:   queries.ecommerce.couponsSelector
})

const mapDispatchToProps = {
  createCoupon: createCoupon
}

export default compose(
  connect<Props, _, _, DispatchProps, _, _>(
    mapStateToProps,
    mapDispatchToProps
  ),
  connectRequest(mapPropsToConfig)
)(CreateCouponPage)
