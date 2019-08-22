// @flow
import React from "react"
import { Dropdown, DropdownToggle, DropdownMenu } from "reactstrap"

import ProductSelectorMenu from "./ProductSelectorMenu"

import { preventDefaultAndInvoke } from "../../lib/util"
import { findRunInProduct, formatRunTitle } from "../../lib/ecommerce"
import { PRODUCT_TYPE_COURSERUN, PRODUCT_TYPE_PROGRAM } from "../../constants"

import type { ProductDetail } from "../../flow/ecommerceTypes"

type Props = {
  products: Array<ProductDetail>,
  field: {
    name: string,
    value: Object,
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
  dropdownOpen: boolean
}
export default class ProductSelector extends React.Component<Props, State> {
  state = {
    productType:  "courserun",
    dropdownOpen: false
  }

  updateProductType = (productType: ProductType) => {
    const {
      field: { name, onChange }
    } = this.props
    if (this.state.productType === productType) {
      return
    }
    this.setState({ productType })
    onChange({ target: { value: "", name } })
  }

  toggleDropdownVisibility = () => {
    this.setState({
      dropdownOpen: !this.state.dropdownOpen
    })
  }

  render() {
    const {
      field: { onChange, name, value },
      products
    } = this.props
    const { dropdownOpen, productType } = this.state
    let selectedProduct, selectedRun
    if (value) {
      selectedProduct = products.find(_product => _product.id === value)
      if (
        selectedProduct &&
        selectedProduct.product_type === PRODUCT_TYPE_COURSERUN
      ) {
        selectedRun = findRunInProduct(selectedProduct)
      }
    }

    return (
      <div className="product-selector">
        <div className="row">
          <div className="col-12">
            <button
              className={`${
                productType === PRODUCT_TYPE_COURSERUN ? "selected" : ""
              } select-product-type`}
              onClick={preventDefaultAndInvoke(() =>
                this.updateProductType("courserun")
              )}
            >
              Course
            </button>
            <button
              className={`${
                productType === PRODUCT_TYPE_PROGRAM ? "selected" : ""
              } select-product-type`}
              onClick={preventDefaultAndInvoke(() =>
                this.updateProductType(PRODUCT_TYPE_PROGRAM)
              )}
            >
              Program
            </button>
          </div>
        </div>

        <div className="row">
          <div className="col-12">
            <span className="description">
              * Choose a{" "}
              {productType === PRODUCT_TYPE_PROGRAM ? "Program" : "Course"}:
            </span>
            <button
              className="select-product"
              onClick={preventDefaultAndInvoke(() =>
                this.toggleDropdownVisibility()
              )}
            >
              Click to select{" "}
              {productType === PRODUCT_TYPE_PROGRAM ? "Program" : "Course"}
            </button>
            <br />
            <Dropdown
              isOpen={dropdownOpen}
              toggle={this.toggleDropdownVisibility}
            >
              <DropdownToggle tag="span" />
              <DropdownMenu>
                <div className="triangle" />
                <ProductSelectorMenu
                  products={products}
                  productType={productType}
                  onChange={onChange}
                  name={name}
                  selectedProductId={value}
                  toggleDropdown={this.toggleDropdownVisibility}
                />
              </DropdownMenu>
            </Dropdown>
            {selectedProduct ? (
              <React.Fragment>
                {selectedProduct.title}
                <br />
                {selectedRun ? (
                  <React.Fragment>
                    {formatRunTitle(selectedRun)}
                    <br />
                  </React.Fragment>
                ) : null}
                <span className="description">
                  {selectedProduct.latest_version.readable_id}
                </span>
              </React.Fragment>
            ) : null}
          </div>
        </div>
      </div>
    )
  }
}
