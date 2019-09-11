// @flow
import React from "react"
import { Button } from "reactstrap"

type Props = {
  title: string,
  children: any,
  className?: string
}
type State = {
  expanded: boolean
}
export default class Expandable extends React.Component<Props, State> {
  state = {
    expanded: false
  }

  render() {
    const { title, children, className } = this.props
    const { expanded } = this.state

    return (
      <div className={`expandable ${className ? className : ""}`}>
        <div
          className="header"
          onClick={() =>
            this.setState({
              expanded: !expanded
            })
          }
        >
          <span className="title">{title}</span>
          <i className="material-icons toggle">
            {expanded ? "expand_less" : "expand_more"}
          </i>
        </div>
        <div className="body">{expanded ? children : null}</div>
      </div>
    )
  }
}
