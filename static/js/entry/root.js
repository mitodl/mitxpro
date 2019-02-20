require("react-hot-loader/patch")
/* global SETTINGS:false */
__webpack_public_path__ = SETTINGS.public_path // eslint-disable-line no-undef, camelcase
import React from "react"
import ReactDOM from "react-dom"
import { AppContainer } from "react-hot-loader"
import { createBrowserHistory } from "history"

import configureStore from "../store/configureStore"
import Router, { routes } from "../Router"

import Raven from "raven-js"

Raven.config(SETTINGS.sentry_dsn, {
  release:     SETTINGS.release_version,
  environment: SETTINGS.environment
}).install()

window.Raven = Raven

// Object.entries polyfill
import entries from "object.entries"
if (!Object.entries) {
  entries.shim()
}

const store = configureStore()

const rootEl = document.getElementById("container")

const renderApp = Component => {
  const history = createBrowserHistory()
  ReactDOM.render(
    <AppContainer>
      <Component history={history} store={store}>
        {routes}
      </Component>
    </AppContainer>,
    rootEl
  )
}

renderApp(Router)

if (module.hot) {
  module.hot.accept("../Router", () => {
    const RouterNext = require("../Router").default
    renderApp(RouterNext)
  })
}
