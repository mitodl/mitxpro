// @flow
import React from "react"
import _ from "lodash"
import { connectRequest, mutateAsync } from "redux-query"
import { compose } from "redux"
import { connect } from "react-redux"

import { CouponForm } from "../../components/forms/CouponForm"
import queries from "../../lib/queries"

import type { Response } from "redux-query"
import type {
  Company,
  CouponPaymentVersion,
  Product
} from "../../flow/ecommerceTypes"

type State = {
  isPromo: boolean,
  selectedProducts: Array<Product>,
  productType: string,
  created: boolean
}

type StateProps = {|
  products: Array<Product>,
  companies: Array<Company>,
  newCoupon: CouponPaymentVersion
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
      isPromo:          false,
      productType:      "courserun",
      selectedProducts: [],
      created:          false
    }
  }
  onSubmit = async (coupon: Object, { setSubmitting, setErrors }: Object) => {
    const { createCoupon } = this.props
    coupon.product_ids = coupon.products.map(product => product.id)
    if (coupon.coupon_type === "single-use") {
      coupon.max_redemptions = coupon.num_coupon_codes
    } else {
      coupon.num_coupon_codes = 1
    }
    coupon.amount = coupon.amount / 100
    try {
      const result = await createCoupon(coupon)
      if (result && result.transformed) {
        this.setState({ created: true })
      } else if (result.body && result.body.errors) {
        setErrors(_.merge({}, ...result.body.errors))
        this.setState({ created: false })
      }
    } finally {
      setSubmitting(false)
    }
  }

  toggleCouponType = async () => {
    const { isPromo } = this.state
    await this.setState({ isPromo: !isPromo })
  }

  toggleProductType = async (event: Object) => {
    await this.setState({
      productType:      event.target.value,
      selectedProducts: []
    })
  }

  clearSuccess = async () => {
    await this.setState({ created: false, selectedProducts: [] })
  }

  filterProducts = () => {
    const { productType } = this.state
    const { products } = this.props
    return _.filter(products, { product_type: productType })
  }

  selectProducts = async (value: any) => {
    await this.setState({ selectedProducts: value })
  }

  render() {
    const { isPromo, productType, selectedProducts, created } = this.state
    const { newCoupon, companies } = this.props
    return (
      <div className="coupon-creation-div">
        <h3>Create a coupon</h3>
        {created && newCoupon ? (
          <div className="coupon-success-div">
            {newCoupon.coupon_type === "promo" ? (
              <span>{`Coupon "${
                newCoupon.payment.name
              }" successfully created.`}</span>
            ) : (
              <a href={`/couponcodes/${newCoupon.id}`}>
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
            toggleForm={this.toggleCouponType}
            toggleProduct={this.toggleProductType}
            isPromo={isPromo}
            productType={productType}
            products={this.filterProducts()}
            companies={companies}
            selectProducts={this.selectProducts}
            selectedProducts={selectedProducts}
          />
        )}
      </div>
    )
  }
}

const createCoupon = (coupon: Object) =>
  mutateAsync(queries.ecommerce.newCouponMutation(coupon))

const mapPropsToConfig = () => [
  queries.ecommerce.productsQuery(),
  queries.ecommerce.companiesQuery()
]

const mapStateToProps = (state: Object): StateProps => ({
  products:  queries.ecommerce.productsSelector(state),
  companies: queries.ecommerce.companiesSelector(state),
  newCoupon: queries.ecommerce.newCouponSelector(state)
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
