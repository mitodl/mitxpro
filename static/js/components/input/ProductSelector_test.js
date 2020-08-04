// @flow
import React from "react"
import * as R from "ramda"
import sinon from "sinon"
import { shallow } from "enzyme"
import { assert } from "chai"
import casual from "casual-browserify"
// $FlowFixMe: Flow trips up with this library
import Select from "react-select"

import ProductSelector, {
  productTypeLabels,
  productDateSortCompare,
  ProductSelector as InnerProductSelector
} from "./ProductSelector"

import { makeCourse } from "../../factories/course"
import { makeSimpleProduct, makeProgramRun } from "../../factories/ecommerce"
import { PRODUCT_TYPE_COURSERUN, PRODUCT_TYPE_PROGRAM } from "../../constants"
import {
  findRunInProduct,
  formatCoursewareDate,
  formatRunTitle
} from "../../lib/ecommerce"
import { shouldIf } from "../../lib/test_utils"
import IntegrationTestHelper from "../../util/integration_test_helper"
import type { ProgramRunDetail } from "../../flow/ecommerceTypes"

// When a component with a <Select /> is rendered with shallow(), it appears as
// a <StateManager /> with className="select"
const SelectComponentSelector = "StateManager.select"

const generateCourseRunParent = () => {
  const course = makeCourse()
  return {
    id:    course.id,
    title: course.title
  }
}

describe("ProductSelector", () => {
  let defaultProps,
    products,
    onChangeStub,
    runProduct2Course1,
    runProduct1Course1,
    runProduct2,
    programProduct

  beforeEach(() => {
    onChangeStub = sinon.createSandbox().stub()
    const courseRunParent = generateCourseRunParent()
    runProduct1Course1 = makeSimpleProduct(PRODUCT_TYPE_COURSERUN)
    runProduct2Course1 = makeSimpleProduct(PRODUCT_TYPE_COURSERUN)
    runProduct1Course1.parent = courseRunParent
    runProduct2Course1.parent = courseRunParent
    runProduct2 = makeSimpleProduct(PRODUCT_TYPE_COURSERUN)
    programProduct = makeSimpleProduct(PRODUCT_TYPE_PROGRAM, "test+Aug_2016")

    products = [
      runProduct2,
      programProduct,
      runProduct1Course1,
      runProduct2Course1
    ]
    defaultProps = {
      field: {
        name:     "derp",
        value:    null,
        onChange: onChangeStub,
        onBlur:   () => {}
      },
      form: {
        touched: false,
        errors:  {},
        values:  {}
      },
      products:           products,
      selectedProduct:    null,
      programRunsLoading: false,
      programRuns:        [],
      fetchProgramRuns:   () => {}
    }
  })
  ;[PRODUCT_TYPE_COURSERUN, PRODUCT_TYPE_PROGRAM].forEach(productType => {
    describe(`for productType ${productType}`, () => {
      it("renders product type and courseware object Select widgets", () => {
        const wrapper = shallow(<InnerProductSelector {...defaultProps} />)
        wrapper.setState({ productType })
        const select = wrapper.find(SelectComponentSelector).at(0)
        assert.deepEqual(select.prop("options"), [
          {
            label: "Course",
            value: PRODUCT_TYPE_COURSERUN
          },
          {
            label: "Program",
            value: PRODUCT_TYPE_PROGRAM
          }
        ])
        assert.equal(
          wrapper.find(".product-row .description").text(),
          `Select ${productTypeLabels[productType]}:`
        )
        const coursewareObjSelect = wrapper.find(SelectComponentSelector).at(1)
        assert.isNull(coursewareObjSelect.prop("value"))
      })

      it("should update the state when the product type Select option is changed", () => {
        const wrapper = shallow(<InnerProductSelector {...defaultProps} />)
        wrapper.setState({ productType })
        const opposite =
          productType === PRODUCT_TYPE_PROGRAM
            ? PRODUCT_TYPE_COURSERUN
            : PRODUCT_TYPE_PROGRAM
        const selectWrapper = wrapper.find(SelectComponentSelector).at(0)
        selectWrapper.prop("onChange")({
          value: opposite,
          label: productTypeLabels[productType]
        })
        assert.equal(wrapper.state().productType, opposite)
      })
    })
  })

  it("renders a list of programs", () => {
    const wrapper = shallow(<InnerProductSelector {...defaultProps} />)
    wrapper.setState({ productType: PRODUCT_TYPE_PROGRAM })
    const selectWrapper = wrapper.find(SelectComponentSelector).at(1)
    assert.deepEqual(selectWrapper.prop("options"), [
      {
        label: programProduct.latest_version.content_title,
        value: programProduct.id
      }
    ])
  })

  it("preselects a program product when selectedProduct is passed in", () => {
    const selectedProduct = programProduct
    const wrapper = shallow(
      <InnerProductSelector
        {...defaultProps}
        selectedProduct={selectedProduct}
      />
    )
    const selectWrapper = wrapper.find(SelectComponentSelector).at(1)
    assert.deepEqual(selectWrapper.prop("value"), {
      value: selectedProduct.id,
      label: selectedProduct.latest_version.content_title
    })
  })

  it("renders a list of unique courses", () => {
    const wrapper = shallow(<InnerProductSelector {...defaultProps} />)
    wrapper.setState({ productType: PRODUCT_TYPE_COURSERUN })
    const selectWrapper = wrapper.find(SelectComponentSelector).at(1)
    const courseProducts = products.filter(
      product => product.product_type === PRODUCT_TYPE_COURSERUN
    )
    // If multiple runs belong to the same course, that course should only show up once in the options
    const expectedOptions = [
      {
        label: runProduct2.parent.title,
        value: runProduct2.parent.id
      },
      {
        label: runProduct1Course1.parent.title,
        value: runProduct1Course1.parent.id
      }
    ]
    assert.deepEqual(selectWrapper.prop("options"), expectedOptions)
    assert.isAbove(courseProducts.length, expectedOptions.length)
  })

  it("preselects a course product when selectedProduct is passed in", () => {
    const selectedProduct = runProduct1Course1
    const wrapper = shallow(
      <InnerProductSelector
        {...defaultProps}
        selectedProduct={selectedProduct}
      />
    )
    const selectWrapper = wrapper.find(SelectComponentSelector).at(1)
    assert.deepEqual(selectWrapper.prop("value"), {
      value: selectedProduct.parent.id,
      label: selectedProduct.parent.title
    })
  })

  it("doesn't render a list of course run dates if the program type is selected", () => {
    const wrapper = shallow(<InnerProductSelector {...defaultProps} />)
    wrapper.setState({
      productType: PRODUCT_TYPE_PROGRAM
    })
    assert.isFalse(
      wrapper
        .find(SelectComponentSelector)
        .at(2)
        .exists()
    )
  })

  it("renders a list of course run dates if the course type is selected", () => {
    const wrapper = shallow(<InnerProductSelector {...defaultProps} />)
    wrapper.setState({
      productType:           PRODUCT_TYPE_COURSERUN,
      selectedCoursewareObj: {
        label: runProduct2Course1.parent.title,
        value: runProduct2Course1.parent.id
      }
    })

    const selectWrapper = wrapper.find(SelectComponentSelector).at(2)
    const expectedProducts = [runProduct1Course1, runProduct2Course1]
    assert.deepEqual(
      selectWrapper.prop("options"),
      expectedProducts.sort(productDateSortCompare).map(product => ({
        label: `${formatCoursewareDate(
          product.start_date
        )} - ${formatCoursewareDate(product.end_date)}`,
        value: product.id
      }))
    )
  })

  it("sets the selected product when a program is selected", () => {
    const wrapper = shallow(<InnerProductSelector {...defaultProps} />)
    wrapper.setState({
      productType: PRODUCT_TYPE_PROGRAM
    })
    sinon.assert.calledWith(onChangeStub, {
      target: {
        name:  defaultProps.field.name,
        value: { productId: null, programRunId: null }
      }
    })
    wrapper.setState({
      selectedCoursewareObj: {
        label: programProduct.latest_version.content_title,
        value: programProduct.id
      },
      selectedCourseDate: null
    })
    sinon.assert.calledWith(onChangeStub, {
      target: {
        name:  defaultProps.field.name,
        value: { productId: programProduct.id, programRunId: null }
      }
    })
  })

  it("renders a list of available program runs when a program is selected", () => {
    const programRuns = [
      makeProgramRun(programProduct.latest_version),
      makeProgramRun(programProduct.latest_version)
    ]
    const props = Object.assign(defaultProps, { programRuns })
    const wrapper = shallow(<InnerProductSelector {...props} />)
    wrapper.setState({
      productType:           PRODUCT_TYPE_PROGRAM,
      selectedCoursewareObj: {
        label: programProduct.latest_version.content_title,
        value: programProduct.id
      }
    })
    const selectWrapper = wrapper.find(SelectComponentSelector).at(2)
    assert.deepEqual(
      selectWrapper.prop("options"),
      programRuns.sort(productDateSortCompare).map(programRun => ({
        label: `${formatCoursewareDate(
          programRun.start_date
        )} - ${formatCoursewareDate(programRun.end_date)}`,
        value: programRun.id
      }))
    )
  })

  it("sets the selected program run when one is selected", () => {
    const programRuns = [
      makeProgramRun(programProduct.latest_version),
      makeProgramRun(programProduct.latest_version)
    ]
    const props = Object.assign(defaultProps, { programRuns })
    const wrapper = shallow(<InnerProductSelector {...props} />)
    wrapper.setState({
      productType:           PRODUCT_TYPE_PROGRAM,
      selectedCoursewareObj: {
        label: programProduct.latest_version.content_title,
        value: programProduct.id
      },
      selectedCourseDate: null
    })
    sinon.assert.calledWith(onChangeStub, {
      target: {
        name:  defaultProps.field.name,
        value: { productId: programProduct.id, programRunId: null }
      }
    })
    const dateSelectWrapper = wrapper.find(SelectComponentSelector).at(2)
    const option = dateSelectWrapper.prop("options")[0]
    dateSelectWrapper.prop("onChange")(option)
    sinon.assert.calledWith(onChangeStub, {
      target: {
        name:  defaultProps.field.name,
        value: { productId: programProduct.id, programRunId: option.value }
      }
    })
  })

  it("sets the selected product when a course date is selected", () => {
    const wrapper = shallow(<InnerProductSelector {...defaultProps} />)
    const product = runProduct1Course1
    wrapper.setState({
      productType:           PRODUCT_TYPE_COURSERUN,
      selectedCoursewareObj: {
        label: product.parent.title,
        value: product.parent.id
      }
    })
    sinon.assert.calledWith(onChangeStub, {
      target: {
        name:  defaultProps.field.name,
        value: { productId: null, programRunId: null }
      }
    })
    const dateSelectWrapper = wrapper.find(SelectComponentSelector).at(2)
    const option = dateSelectWrapper.prop("options")[0]
    dateSelectWrapper.prop("onChange")(option)
    sinon.assert.calledWith(onChangeStub, {
      target: {
        name:  defaultProps.field.name,
        value: { productId: option.value, programRunId: null }
      }
    })
  })
})
