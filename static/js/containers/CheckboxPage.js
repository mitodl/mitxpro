// @flow
import React from "react"
import { connect } from "react-redux"
import type { Match } from "react-router"
import type { Dispatch } from "redux"

import { updateCheckbox } from "../actions"

class CheckboxPage extends React.Component<*, void> {
  props: {
    dispatch: Dispatch<*>,
    checkbox: {
      checked: boolean
    },
    match: Match
  }

  handleClick(e) {
    const { dispatch } = this.props
    dispatch(updateCheckbox(e.target.checked))
  }

  render() {
    const { checked } = this.props.checkbox
    return (
      <div>
        <div id="app-body">
          Click the checkbox:
          <input
            type="checkbox"
            checked={checked}
            onClick={this.handleClick.bind(this)}
          />
        </div>
      </div>
    )
  }
}

const mapStateToProps = state => {
  return {
    checkbox: state.checkbox
  }
}

export default connect(mapStateToProps)(CheckboxPage)
