// @flow
import React from "react"

import { preventDefaultAndInvoke } from "../../lib/util"

import type { Product } from "../../flow/ecommerceTypes"

type Props = {
  products: Array<Product>,
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
  productType: ProductType
}
export default class ProductSelector extends React.Component<Props, State> {
  state = {
    productType: "courserun"
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

  render() {
    const {
      field: { onChange, name, value },
      products
    } = this.props
    const { productType } = this.state

    return (
      <div className="product-selector">
        <div className="row">
          <div className="col-12">
            <button
              className={productType === "courserun" ? "selected" : ""}
              onClick={preventDefaultAndInvoke(() =>
                this.updateProductType("courserun")
              )}
            >
              Course
            </button>
            <button
              className={productType === "program" ? "selected" : ""}
              onClick={preventDefaultAndInvoke(() =>
                this.updateProductType("program")
              )}
            >
              Program
            </button>
          </div>
        </div>

        <div className="row">
          <div className="col-12">
            <select onChange={onChange} name={name} value={value.product}>
              <option value={""} key={"null"}>
                Select a product
              </option>
              {products
                .filter(product => product.product_type === productType)
                .map(product => (
                  <option value={product.id} key={product.id}>
                    {product.title}
                  </option>
                ))}
            </select>
          </div>
        </div>
      </div>
    )
  }
}
