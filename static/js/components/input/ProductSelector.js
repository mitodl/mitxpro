// @flow
import React from "react"
// $FlowFixMe: Flow trips up with this library
import Select from "react-select"

import { findRunInProduct, formatRunTitle } from "../../lib/ecommerce"
import { PRODUCT_TYPE_COURSERUN, PRODUCT_TYPE_PROGRAM } from "../../constants"

import type { ProductDetail } from "../../flow/ecommerceTypes"
import type { Course, CourseRun } from "../../flow/courseTypes"

const productTypeOptions = [
  { value: PRODUCT_TYPE_COURSERUN, label: "Course" },
  { value: PRODUCT_TYPE_PROGRAM, label: "Program" }
]

const makeProductOption = (
  product: ProductDetail,
  run?: CourseRun,
  course?: Course
) => ({
  value: product.id,
  label:
    product.product_type === PRODUCT_TYPE_PROGRAM || !course
      ? product.title
      : course.title
})

const makeProductRunOption = (product: ProductDetail) => {
  const [run] = findRunInProduct(product)

  console.log("run", product.id, formatRunTitle(run), run)
  return {
    label: formatRunTitle(run),
    value: product.id
  }
}

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
  selected: [?ProductDetail, ?CourseRun, ?Course]
}
type SelectOption = {
  label: string,
  value: number | string
}
export default class ProductSelector extends React.Component<Props, State> {
  state = {
    productType: PRODUCT_TYPE_COURSERUN,
    selected:    [null, null, null]
  }

  calcProductOptions = (): Array<SelectOption> => {
    const { products } = this.props
    const { productType } = this.state

    const filteredProducts = products.filter(
      product => product.product_type === productType
    )
    if (productType === PRODUCT_TYPE_PROGRAM) {
      return filteredProducts.map(product => makeProductOption(product))
    }

    const productRuns = products
      .filter(_product => _product.product_type === PRODUCT_TYPE_COURSERUN)
      .map(_product => [_product, ...findRunInProduct(_product)])

    const courseIds = new Set()
    const productOptions = []
    for (const [product, run, course] of productRuns) {
      if (run && course && !courseIds.has(course.id)) {
        courseIds.add(course.id)
        productOptions.push(makeProductOption(product, run, course))
      }
    }
    return productOptions
  }

  calcSelectedProduct = () => {
    const {
      products,
      field: { value }
    } = this.props
    const {
      productType,
      selected: [selectedProduct, selectedRun, selectedCourse]
    } = this.state

    if (productType === PRODUCT_TYPE_PROGRAM) {
      return products.find(_product => _product.id === value)
    }

    return selectedProduct
      // $FlowFixMe: Flow is confused by selectedProduct here
      ? makeProductOption(selectedProduct, selectedRun, selectedCourse)
      : null
  }

  updateSelectedProduct = (productOption: SelectOption) => {
    const {
      field: { name, value, onChange },
      products
    } = this.props
    const {
      productType,
      selected: [selectedProduct]
    } = this.state
    if (productOption.value === value) {
      return
    }

    if (productType === PRODUCT_TYPE_PROGRAM) {
      onChange({ target: { name, value: productOption.value } })
    } else {
      const product = products.find(
        _product => _product.id === productOption.value
      )
      if (!product) {
        // make flow happy
        return
      }

      if (selectedProduct && product.id === selectedProduct.id) {
        return
      }

      this.setState({
        selected: [product, ...findRunInProduct(product)]
      })
      onChange({ target: { name, value: null } })
    }
  }

  calcProductDateOptions = (): Array<*> => {
    const { products } = this.props
    const {
      selected: [selectedProduct, selectedRun, selectedCourse]
    } = this.state

    return products
      .filter(product => {
        if (
          product.product_type !== PRODUCT_TYPE_COURSERUN ||
          !selectedCourse
        ) {
          return false
        }
        const [run, course] = findRunInProduct(product)
        // should only be one course for a course run product
        return course && course.id === selectedCourse.id
      })
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
      selected: [null, null, null]
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
