/* global require:false, module:false */
import { prop } from "ramda"
import { compose, createStore, applyMiddleware } from "redux"
import { createLogger } from "redux-logger"
import { queryMiddleware } from "redux-query"

import rootReducer from "../reducers"

// Setup middleware
const COMMON_MIDDLEWARE = [queryMiddleware(prop("queries"), prop("entities"))]

// Store factory configuration
let createStoreWithMiddleware
if (process.env.NODE_ENV !== "production") {
  createStoreWithMiddleware = compose(
    applyMiddleware(...COMMON_MIDDLEWARE, createLogger()),
    window.__REDUX_DEVTOOLS_EXTENSION__
      ? window.__REDUX_DEVTOOLS_EXTENSION__()
      : f => f
  )(createStore)
} else {
  createStoreWithMiddleware = compose(applyMiddleware(...COMMON_MIDDLEWARE))(
    createStore
  )
}

export default function configureStore(initialState: Object) {
  const store = createStoreWithMiddleware(rootReducer, initialState)

  if (module.hot) {
    // Enable Webpack hot module replacement for reducers
    module.hot.accept("../reducers", () => {
      const nextRootReducer = require("../reducers")

      store.replaceReducer(nextRootReducer)
    })
  }

  return store
}
