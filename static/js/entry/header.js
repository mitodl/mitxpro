import React from "react"
import ReactDOM from "react-dom"
import { Provider } from "react-redux"
import { AppContainer } from "react-hot-loader"
import { Router as ReactRouter } from "react-router"
import { createBrowserHistory } from "history"

import configureStore from "../store/configureStore"
import { AppTypeContext, MIXED_APP_CONTEXT } from "../contextDefinitions"
import HeaderApp from "../containers/HeaderApp"
// Object.entries polyfill
import entries from "object.entries"

require("react-hot-loader/patch")
/* global SETTINGS:false */
__webpack_public_path__ = SETTINGS.public_path // eslint-disable-line no-undef, camelcase

if (!Object.entries) {
  entries.shim()
}

const store = configureStore()

const rootEl = document.getElementById("header")

const renderHeader = () => {
  const history = createBrowserHistory()
  ReactDOM.render(
    <AppContainer>
      <Provider store={store}>
        <AppTypeContext.Provider value={MIXED_APP_CONTEXT}>
          <ReactRouter history={history}>
            <HeaderApp />
          </ReactRouter>
        </AppTypeContext.Provider>
      </Provider>
    </AppContainer>,
    rootEl
  )
}

renderHeader()
