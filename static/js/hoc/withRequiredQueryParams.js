// @flow
import React from "react"
import qs from "query-string"
import { createStructuredSelector } from "reselect"
import { curry } from "ramda"

import { anyKeyEmptyOrNil } from "../lib/util"

const withRequiredParams = curry(
  (
    requiredParams: Array<string>,
    ErrorComponent: Class<React.Component<*, *>>,
    WrappedComponent: Class<React.Component<*, *>>
  ) => {
    class WithRequiredParams extends React.Component<*> {
      static WrappedComponent: Class<React.Component<*, *>>

      render() {
        const { params } = this.props

        if (anyKeyEmptyOrNil(requiredParams, params || {})) {
          return <ErrorComponent />
        }

        return <WrappedComponent {...this.props} />
      }
    }

    WithRequiredParams.WrappedComponent = WrappedComponent
    WithRequiredParams.displayName = `withRequiredParams(${
      WrappedComponent.name
    })`
    return WithRequiredParams
  }
)

export default withRequiredParams
