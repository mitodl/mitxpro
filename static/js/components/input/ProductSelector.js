// @flow
import React from "react"
// $FlowFixMe: Flow trips up with this library
import Select from "react-select"

import { findRunInProduct, formatRunTitle } from "../../lib/ecommerce"
import { PRODUCT_TYPE_COURSERUN, PRODUCT_TYPE_PROGRAM } from "../../constants"

import type { ProductDetail } from "../../flow/ecommerceTypes"

const productTypeOptions = [
  { value: PRODUCT_TYPE_COURSERUN, label: "Course" },
  { value: PRODUCT_TYPE_PROGRAM, label: "Program" }
]

const makeProductOption = (product: ProductDetail) => ({
  value: product.id,
  label: product.title
})

const makeProductRunOption = (product: ProductDetail) => ({
  label: formatRunTitle(findRunInProduct(product)),
  value: product.id
})

type Props = {
  products: Array<ProductDetail>,
  field: {
    name: string,
    value: ?number,
    onChange: Function,
    onBlur: Function
  },
  form: {
    touched: boolean,
    errors: Object,
    values: Object
  }
}
type ProductType = "courserun" | "program"
type State = {
  productType: ProductType,
  selectedCourseProduct: ?ProductDetail
}
type SelectOption = {
  label: string,
  value: number | string
}
export default class ProductSelector extends React.Component<Props, State> {
  state = {
    productType:           PRODUCT_TYPE_COURSERUN,
    selectedCourseProduct: null
  }

  calcProductOptions = (): Array<SelectOption> => {
    const { products } = this.props
    const { productType } = this.state

    const filteredProducts = products.filter(
      _product => _product.product_type === productType
    )
    if (productType === PRODUCT_TYPE_PROGRAM) {
      return filteredProducts.map(makeProductOption)
    }

    const productRuns = products
      .filter(_product => _product.product_type === PRODUCT_TYPE_COURSERUN)
      .map(_product => [_product, findRunInProduct(_product)])

    const runIds = new Set()
    const productOptions = []
    for (const [product, run] of productRuns) {
      if (run && !runIds.has(run.id)) {
        runIds.add(run.id)
        productOptions.push(makeProductOption(product))
      }
    }
    return productOptions
  }

  calcSelectedProduct = () => {
    const {
      products,
      field: { value }
    } = this.props
    const { productType, selectedCourseProduct } = this.state

    const selectedProduct =
      productType === PRODUCT_TYPE_PROGRAM
        ? products.find(_product => _product.id === value)
        : selectedCourseProduct

    return selectedProduct ? makeProductOption(selectedProduct) : null
  }

  updateSelectedProduct = (productOption: SelectOption) => {
    const {
      field: { name, value, onChange },
      products
    } = this.props
    const { productType, selectedCourseProduct } = this.state
    if (productOption.value === value) {
      return
    }

    if (productType === PRODUCT_TYPE_PROGRAM) {
      onChange({ target: { name, value: productOption.value } })
    } else {
      const product = products.find(
        _product => _product.id === productOption.value
      )
      if (
        selectedCourseProduct &&
        product &&
        product.id === selectedCourseProduct.id
      ) {
        return
      }
      this.setState({
        selectedCourseProduct: product
      })
      onChange({ target: { name, value: null } })
    }
  }

  calcProductDateOptions = (): Array<*> => {
    const { products } = this.props
    const { selectedCourseProduct } = this.state

    const courseId = selectedCourseProduct
      ? selectedCourseProduct.latest_version.courses[0].id
      : null

    return products
      .filter(
        product =>
          product.product_type === PRODUCT_TYPE_COURSERUN &&
          // should only be one course for a course run product
          product.latest_version.courses[0].id === courseId
      )
      .map(makeProductRunOption)
  }

  calcSelectedProductDate = () => {
    const {
      field: { value },
      products
    } = this.props

    const product = products.find(product => product.id === value)
    return product ? makeProductRunOption(product) : null
  }

  updateProductType = (productType: ProductType) => {
    const {
      field: { name, onChange }
    } = this.props
    if (this.state.productType === productType) {
      return
    }
    this.setState({
      productType,
      selectedCourseProduct: null
    })
    onChange({ target: { value: "", name } })
  }

  render() {
    const {
      field: { onChange, name }
    } = this.props
    const { productType } = this.state

    const productTypeText =
      productType === PRODUCT_TYPE_PROGRAM ? "program" : "course"

    return (
      <div className="product-selector">
        <div className="row course-row">
          <div className="col-12">
            <span className="description">
              Select to view available courses or programs:
            </span>
            <Select
              className="select"
              options={productTypeOptions}
              components={{ IndicatorSeparator: null }}
              onChange={selectedOption =>
                this.updateProductType(
                  // $FlowFixMe: thinks selectedOption could be an array
                  selectedOption ? selectedOption.value : null
                )
              }
              value={productTypeOptions.find(
                option => option.value === productType
              )}
            />
          </div>
        </div>

        <div className="row product-row">
          <div className="col-12">
            <span className="description">
              Select available {productTypeText}:
            </span>
            <Select
              className="select"
              components={{ IndicatorSeparator: null }}
              options={this.calcProductOptions()}
              value={this.calcSelectedProduct()}
              onChange={this.updateSelectedProduct}
            />
          </div>
        </div>

        {productType === PRODUCT_TYPE_COURSERUN ? (
          <div className="row course-date-row">
            <div className="col-12">
              <span className="description">Select start date:</span>
              <Select
                className="select"
                components={{ IndicatorSeparator: null }}
                options={this.calcProductDateOptions()}
                value={this.calcSelectedProductDate()}
                onChange={selectedProduct => {
                  onChange({
                    target: {
                      name,
                      // $FlowFixMe: seems to think selectedProduct is an array here
                      value: selectedProduct ? selectedProduct.value : null
                    }
                  })
                }}
              />
            </div>
          </div>
        ) : null}
      </div>
    )
  }
}
