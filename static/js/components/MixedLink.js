// @flow
import React from "react"
import { omit } from "ramda"
import { Link } from "react-router-dom"

import { AppTypeContext, SPA_APP_CONTEXT } from "../contextDefinitions"

type MixedLinkProps = {
  children: any,
  dest: string
} & any

export default class MixedLink extends React.Component<MixedLinkProps, *> {
  render() {
    const { children, dest } = this.props

    const otherProps = omit(["children", "dest"], this.props)

    return (
      <AppTypeContext.Consumer>
        {appType =>
          appType === SPA_APP_CONTEXT ? (
            <Link to={dest} {...otherProps}>
              {children}
            </Link>
          ) : (
            <a href={dest} {...otherProps}>
              {children}
            </a>
          )
        }
      </AppTypeContext.Consumer>
    )
  }
}
