// @flow
import React from "react"
// $FlowFixMe: Flow trips up with this library
import Select from "react-select"
import * as R from "ramda"

import { formatCoursewareDate } from "../../lib/ecommerce"
import { PRODUCT_TYPE_COURSERUN, PRODUCT_TYPE_PROGRAM } from "../../constants"

import type { SimpleProductDetail } from "../../flow/ecommerceTypes"
import type { Course } from "../../flow/courseTypes"
import { anyNil } from "../../lib/util"

export const productTypeLabels = {
  [PRODUCT_TYPE_COURSERUN]: "Course",
  [PRODUCT_TYPE_PROGRAM]:   "Program"
}
const defaultSelectComponentsProp = { IndicatorSeparator: null }

type Props = {
  field: {
    name: string,
    value: any,
    onChange: Function,
    onBlur: Function
  },
  form: {
    touched: boolean,
    errors: Object,
    values: Object
  },
  products: Array<SimpleProductDetail>,
  selectedProduct: ?SimpleProductDetail
}
type SelectOption = {
  label: string,
  value: number | string
}
type ProductType = PRODUCT_TYPE_COURSERUN | PRODUCT_TYPE_PROGRAM
type State = {
  productType: ProductType,
  selectedCoursewareObj: ?SelectOption,
  selectedCourseDate: ?SelectOption,
  initialized: boolean
}

const buildProgramOption = (product: SimpleProductDetail): SelectOption => ({
  value: product.id,
  label: product.latest_version.content_title
})

const buildCourseOption = (product: SimpleProductDetail): SelectOption => ({
  value: product.parent.id || "",
  label: product.parent.title || ""
})

const buildCourseDateOption = (product: SimpleProductDetail): SelectOption => ({
  value: product.id,
  label: `${formatCoursewareDate(product.start_date)} - ${formatCoursewareDate(
    product.end_date
  )}`
})

export const productDateSortCompare = (
  firstProduct: SimpleProductDetail,
  secondProduct: SimpleProductDetail
) => {
  if (!firstProduct.start_date) {
    return 1
  }
  if (!secondProduct.start_date) {
    return -1
  }
  return firstProduct.start_date < secondProduct.start_date ? -1 : 1
}

export default class ProductSelector extends React.Component<Props, State> {
  state = {
    productType:           PRODUCT_TYPE_COURSERUN,
    selectedCoursewareObj: null,
    selectedCourseDate:    null,
    initialized:           false
  }

  componentDidUpdate(prevProps: Props, prevState: State) {
    if (!R.equals(prevState, this.state)) {
      this.updateSelectedProduct()
    }
  }

  calcProductOptions = (): Array<SelectOption> => {
    const { products } = this.props
    const { productType } = this.state

    const filteredProducts = products.filter(
      product => product.product_type === productType
    )
    if (productType === PRODUCT_TYPE_PROGRAM) {
      return filteredProducts.map(buildProgramOption)
    }

    return R.compose(
      R.uniq,
      R.map(buildCourseOption)
    )(filteredProducts)
  }

  calcProductDateOptions = (): Array<SelectOption> => {
    const { products } = this.props
    const { selectedCoursewareObj } = this.state

    if (!selectedCoursewareObj) {
      return []
    }

    return products
      .filter(
        product =>
          product.product_type === PRODUCT_TYPE_COURSERUN &&
          product.parent.id === selectedCoursewareObj.value
      )
      .sort(productDateSortCompare)
      .map(buildCourseDateOption)
  }

  setProductType = (selectedOption: SelectOption) => {
    const { productType } = this.state

    if (selectedOption.value === productType) {
      return
    }
    this.setState({
      productType:           selectedOption.value,
      selectedCoursewareObj: null,
      selectedCourseDate:    null
    })
  }

  setSelectedCoursewareObj = (selectedOption: SelectOption) => {
    const { selectedCoursewareObj } = this.state

    if (selectedOption === selectedCoursewareObj) {
      return
    }
    this.setState({
      selectedCoursewareObj: selectedOption,
      selectedCourseDate:    null
    })
  }

  setSelectedCourseDate = (selectedOption: SelectOption) => {
    const { selectedCourseDate } = this.state

    if (selectedOption === selectedCourseDate) {
      return
    }
    this.setState({
      selectedCourseDate: selectedOption
    })
  }

  updateSelectedProduct = () => {
    const {
      field: { name, onChange }
    } = this.props
    const {
      productType,
      selectedCoursewareObj,
      selectedCourseDate
    } = this.state
    let productValue

    if (
      (productType === PRODUCT_TYPE_PROGRAM && !selectedCoursewareObj) ||
      (productType === PRODUCT_TYPE_COURSERUN &&
        anyNil([selectedCoursewareObj, selectedCourseDate]))
    ) {
      onChange({ target: { name, value: null } })
      return
    }

    if (productType === PRODUCT_TYPE_PROGRAM) {
      // $FlowFixMe: Can't be null/undefined
      productValue = selectedCoursewareObj.value
    } else {
      // $FlowFixMe: Can't be null/undefined
      productValue = selectedCourseDate.value
    }
    onChange({ target: { name, value: productValue } })
  }

  static getDerivedStateFromProps(props: Props, state: State) {
    if (!props.selectedProduct || state.initialized) {
      return null
    }
    const productType = props.selectedProduct.product_type
    let selectedCoursewareObj, selectedCourseDate
    if (productType === PRODUCT_TYPE_PROGRAM) {
      selectedCoursewareObj = buildProgramOption(props.selectedProduct)
    } else {
      selectedCoursewareObj = buildCourseOption(props.selectedProduct)
      // $FlowFixMe: selectedProduct can't be null/undefined
      selectedCourseDate = buildCourseDateOption(props.selectedProduct)
    }

    return {
      productType,
      selectedCoursewareObj,
      selectedCourseDate,
      initialized: true
    }
  }

  render() {
    const {
      productType,
      selectedCoursewareObj,
      selectedCourseDate
    } = this.state

    return (
      <div className="product-selector">
        <div className="row course-row">
          <div className="col-12">
            <span className="description">
              Select to view available courses or programs:
            </span>
            <Select
              className="select"
              options={Object.keys(productTypeLabels).map(productTypeKey => ({
                value: productTypeKey,
                label: productTypeLabels[productTypeKey]
              }))}
              components={defaultSelectComponentsProp}
              onChange={this.setProductType}
              value={{
                value: productType,
                label: productTypeLabels[productType]
              }}
            />
          </div>
        </div>

        <div className="row product-row">
          <div className="col-12">
            <span className="description">
              Select {productTypeLabels[productType]}:
            </span>
            <Select
              className="select"
              components={defaultSelectComponentsProp}
              options={this.calcProductOptions()}
              value={selectedCoursewareObj}
              onChange={this.setSelectedCoursewareObj}
            />
          </div>
        </div>

        {productType === PRODUCT_TYPE_COURSERUN ? (
          <div className="row course-date-row">
            <div className="col-12">
              <span className="description">Select start date:</span>
              <Select
                className="select"
                components={defaultSelectComponentsProp}
                options={this.calcProductDateOptions()}
                value={selectedCourseDate}
                onChange={this.setSelectedCourseDate}
              />
            </div>
          </div>
        ) : null}
      </div>
    )
  }
}
