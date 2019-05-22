// @flow
import React from "react"
import { connect } from "react-redux"
import { compose } from "redux"
import { partial } from "ramda"
import { Alert } from "reactstrap"

import { removeUserNotification } from "../actions"
import { newSetWith, newSetWithout, timeoutPromise } from "../lib/util"

const DEFAULT_REMOVE_DELAY_MS = 1000

type Props = {
  userNotifications: Array<string>,
  messageRemoveDelayMs?: number,
  removeUserNotification: Function
}

type State = {
  hiddenNotifications: Set<string>
}

export class NotificationContainer extends React.Component<Props, State> {
  state = {
    hiddenNotifications: new Set()
  }

  onDismiss = (notificationText: string) => {
    const { removeUserNotification, messageRemoveDelayMs } = this.props
    const { hiddenNotifications } = this.state

    // This sets the given message in the local state to be considered hidden, then
    // removes the message from the global state and the local hidden state after a delay.
    // The message could be simply removed from the global state to get rid of it, but the
    // local state and the delay gives the Alert a chance to animate the message out.
    this.setState({
      hiddenNotifications: newSetWith(hiddenNotifications, notificationText)
    })
    return timeoutPromise(() => {
      removeUserNotification(notificationText)
      this.setState({
        hiddenNotifications: newSetWithout(
          hiddenNotifications,
          notificationText
        )
      })
    }, messageRemoveDelayMs || DEFAULT_REMOVE_DELAY_MS)
  }

  render() {
    const { userNotifications } = this.props
    const { hiddenNotifications } = this.state

    return (
      <div className="notifications">
        {Array.from(userNotifications).map((notificationText, i) => (
          <Alert
            key={i}
            color="info"
            className="rounded-0 border-0"
            isOpen={!hiddenNotifications.has(notificationText)}
            toggle={partial(this.onDismiss, [notificationText])}
            fade={true}
          >
            {notificationText}
          </Alert>
        ))}
      </div>
    )
  }
}

const mapStateToProps = state => ({
  userNotifications: state.ui.userNotifications
})

export default compose(
  connect(
    mapStateToProps,
    { removeUserNotification }
  )
)(NotificationContainer)
