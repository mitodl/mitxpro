// @flow
import React from "react"
import { sortBy } from "ramda"

import { preventDefaultAndInvoke } from "../../lib/util"
import { findRunInProduct, formatRunTitle } from "../../lib/ecommerce"
import { PRODUCT_TYPE_COURSERUN } from "../../constants"

import type { ProductDetail } from "../../flow/ecommerceTypes"

type ProductType = "courserun" | "program"
type Props = {
  products: Array<ProductDetail>,
  productType: ProductType,
  onChange: Function,
  name: string,
  toggleDropdown: () => void,
  selectedProductId: ?number
}

const ProductSelectorMenu = ({
  name,
  productType,
  products,
  onChange,
  selectedProductId,
  toggleDropdown
}: Props) => (
  <div className="product-selector-menu">
    <div className="header">
      {productType === PRODUCT_TYPE_COURSERUN ? "Courses" : "Programs"}
    </div>
    <div className="product-selector-menu-items">
      {sortBy(
        product => `${product.title}-${product.latest_version.created_on}`,
        products
      )
        .filter(product => product.product_type === productType)
        .map(product => (
          <div
            key={product.id}
            className={`menu-item ${
              product.id === selectedProductId ? "selected" : ""
            }`}
            onClick={preventDefaultAndInvoke(() => {
              onChange({
                target: {
                  value: product.id,
                  name:  name
                }
              })
              toggleDropdown()
            })}
          >
            <img
              src={product.latest_version.thumbnail_url}
              alt={`Image for ${product.title}`}
            />
            <div className="menu-item-description">
              {product.title}
              <br />
              {productType === PRODUCT_TYPE_COURSERUN
                ? formatRunTitle(findRunInProduct(product))
                : null}
            </div>
          </div>
        ))}
    </div>
  </div>
)

export default ProductSelectorMenu
