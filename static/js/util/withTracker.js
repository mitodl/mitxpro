// @flow
/* global SETTINGS: false */

// From https://github.com/ReactTraining/react-router/issues/4278#issuecomment-299692502
import React from "react"
import ga from "react-ga"

const withTracker = (WrappedComponent: Class<React.Component<*, *>>) => {
  const debug = SETTINGS.reactGaDebug === "true"

  if (SETTINGS.gaTrackingID) {
    ga.initialize(SETTINGS.gaTrackingID, { debug: debug })
  }

  const HOC = (props: Object) => {
    const page = props.location.pathname
    if (SETTINGS.gaTrackingID) {
      ga.pageview(page)
    }
    return <WrappedComponent {...props} />
  }

  return HOC
}

export default withTracker
