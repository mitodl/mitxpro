// @flow
import React from "react"
// $FlowFixMe: Flow trips up with this library
import Select from "react-select"
import * as R from "ramda"
import { connect } from "react-redux"
import { compose } from "redux"

import { formatCoursewareDate } from "../../lib/ecommerce"
import { PRODUCT_TYPE_COURSERUN, PRODUCT_TYPE_PROGRAM } from "../../constants"

import type {
  CourseRunProduct,
  ProgramProduct,
  Product,
  ProgramRunDetail
} from "../../flow/ecommerceTypes"
import type { Course } from "../../flow/courseTypes"
import { anyNil } from "../../lib/util"
import { requestAsync } from "redux-query"
import queries from "../../lib/queries"

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
  products: Array<Product>,
  selectedProduct: ?Product,
  programRunsLoading: boolean,
  programRuns: Array<ProgramRunDetail>,
  fetchProgramRuns: Function
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

const buildProgramOption = (product: ProgramProduct): SelectOption => ({
  value: product.id,
  label: product.latest_version.content_title
})

const buildCourseOption = (product: CourseRunProduct): SelectOption => ({
  value: product.content_object.course.id || "",
  label: product.content_object.course.title || ""
})

const buildCourseDateOption = (product: CourseRunProduct): SelectOption => ({
  value: product.id,
  label: `${formatCoursewareDate(
    product.content_object.start_date
  )} - ${formatCoursewareDate(product.content_object.end_date)}`
})

const buildProgramDateOption = (run: ProgramRunDetail): SelectOption => ({
  value: run.id,
  label: `${formatCoursewareDate(run.start_date)} - ${formatCoursewareDate(
    run.end_date
  )}`
})

export const productDateSortCompare = (
  firstProduct: CourseRunProduct,
  secondProduct: CourseRunProduct
) => {
  if (!firstProduct.content_object.start_date) {
    return 1
  }
  if (!secondProduct.content_object.start_date) {
    return -1
  }
  return firstProduct.content_object.start_date <
    secondProduct.content_object.start_date
    ? -1
    : 1
}

export const programRunDateSortCompare = (
  firstProduct: ProgramRunDetail,
  secondProduct: ProgramRunDetail
) => {
  if (!firstProduct.start_date) {
    return 1
  }
  if (!secondProduct.start_date) {
    return -1
  }
  return firstProduct.start_date < secondProduct.start_date ? -1 : 1
}

const buildCourseDateOptions = R.compose(
  R.map(buildCourseDateOption),
  R.sort(productDateSortCompare)
)
const buildProgramOptions = R.map(buildProgramOption)

const buildProgramDateOptions = R.compose(
  R.map(buildProgramDateOption),
  R.sort(programRunDateSortCompare)
)

export class ProductSelector extends React.Component<Props, State> {
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
      return buildProgramOptions(filteredProducts)
    }

    return R.compose(
      R.uniq,
      R.map(buildCourseOption)
    )(filteredProducts)
  }

  calcProductDateOptions = (
    selectedCoursewareObj: ?SelectOption
  ): Array<SelectOption> => {
    const { products, programRunsLoading, programRuns } = this.props
    const { productType } = this.state
    if (
      !selectedCoursewareObj ||
      (productType === PRODUCT_TYPE_PROGRAM && programRunsLoading)
    ) {
      return []
    }
    //Get today's date
    const todaysDate = new Date()
    if (productType === PRODUCT_TYPE_PROGRAM) {
      return buildProgramDateOptions(
        programRuns.filter(programRun => {
          let endDate = null
          if (programRun.end_date) {
            endDate = new Date(programRun.end_date)
          }
          return endDate === null || endDate >= todaysDate
        })
      )
    } else {
      return buildCourseDateOptions(
        products.filter(product => {
          let enrollmentEndDate = null
          if (product.content_object.enrollment_end) {
            enrollmentEndDate = new Date(product.content_object.enrollment_end)
          }
          return (
            product.product_type === PRODUCT_TYPE_COURSERUN &&
            // $FlowFixMe: flow doesn't seem to understand selectedCoursewareObj will be valid here
            product.content_object.course.id === selectedCoursewareObj.value &&
            (enrollmentEndDate === null || enrollmentEndDate >= todaysDate)
          )
        })
      )
    }
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
    const { selectedCoursewareObj, productType } = this.state
    const { fetchProgramRuns } = this.props

    if (selectedOption === selectedCoursewareObj) {
      return
    }
    this.setState({
      selectedCoursewareObj: selectedOption,
      selectedCourseDate:    null
    })
    if (productType === PRODUCT_TYPE_PROGRAM) {
      fetchProgramRuns(selectedOption.value)
    }
    this.calcProductDateOptions(selectedOption)
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
      onChange({
        target: { name, value: { productId: null, programRunId: null } }
      })
      return
    }

    if (productType === PRODUCT_TYPE_PROGRAM) {
      // This is a dirty hack to support program run tags. Refer to `B2bPurchasePage.onSubmit` for further info.
      productValue = {
        // $FlowFixMe: Can't be null/undefined
        productId:    selectedCoursewareObj.value,
        programRunId: selectedCourseDate ? selectedCourseDate.value : null
      }
    } else {
      productValue = {
        // $FlowFixMe: Can't be null/undefined
        productId:    selectedCourseDate.value,
        programRunId: null
      }
    }
    onChange({ target: { name, value: productValue } })

    // $FlowFixMe
    const { applyCoupon, setFieldError, setFieldTouched, values } = this.props
    if (values) {
      values.product = productValue
      applyCoupon(values, setFieldError, setFieldTouched, null)
    }
  }

  shouldShowDateSelector = (): boolean => {
    const { productType, selectedCoursewareObj } = this.state
    const { programRuns } = this.props
    return (
      productType === PRODUCT_TYPE_COURSERUN ||
      (selectedCoursewareObj !== null &&
        productType === PRODUCT_TYPE_PROGRAM &&
        programRuns &&
        programRuns.length > 0)
    )
  }

  static getDerivedStateFromProps(props: Props, state: State) {
    if (!props.selectedProduct || state.initialized) {
      return null
    }
    const selectedProduct: Product = props.selectedProduct
    let selectedCoursewareObj, selectedCourseDate
    if (selectedProduct.product_type === PRODUCT_TYPE_PROGRAM) {
      // $FlowFixMe: thinks this is a courserun
      selectedCoursewareObj = buildProgramOption(selectedProduct)
      props.fetchProgramRuns(selectedCoursewareObj.value)
    } else if (selectedProduct.product_type === PRODUCT_TYPE_COURSERUN) {
      // $FlowFixMe: thinks this is a program
      selectedCoursewareObj = buildCourseOption(selectedProduct)
      // $FlowFixMe: selectedProduct can't be null/undefined
      selectedCourseDate = buildCourseDateOption(selectedProduct)
    } else {
      throw Error(`Unknown product type: ${selectedProduct.product_type}`)
    }

    return {
      productType: selectedProduct.product_type,
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

    const { programRunsLoading } = this.props

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
        {productType === PRODUCT_TYPE_PROGRAM &&
          selectedCoursewareObj !== null &&
          programRunsLoading && (
          <img
            src="/static/images/loader.gif"
            className="mx-auto d-block"
            alt="Loading..."
          />
        )}
        {this.shouldShowDateSelector() && !programRunsLoading && (
          <div className="row course-date-row">
            <div className="col-12">
              <span className="description">Select start date:</span>
              <Select
                className="select"
                components={defaultSelectComponentsProp}
                options={this.calcProductDateOptions(selectedCoursewareObj)}
                value={selectedCourseDate}
                onChange={this.setSelectedCourseDate}
              />
            </div>
          </div>
        )}
      </div>
    )
  }
}

const mapDispatchToProps = dispatch => ({
  fetchProgramRuns: (productId: string) =>
    dispatch(requestAsync(queries.ecommerce.programRunsQuery(productId)))
})

const mapStateToProps = state => ({
  programRuns:        state.entities.programRuns,
  programRunsLoading: R.pathOr(
    false,
    ["queries", "programRuns", "isPending"],
    state
  )
})

export default compose(
  connect(
    mapStateToProps,
    mapDispatchToProps
  )
)(ProductSelector)
