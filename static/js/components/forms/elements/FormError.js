import React from "react"

type Props = {
  children: any
}

export default class FormError extends React.Component<Props> {
  render() {
    const { children } = this.props
    return <div className="form-error">{children}</div>
  }
}
