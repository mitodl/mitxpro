/* global require:false, module:false */
import { compose, createStore, applyMiddleware } from "redux"
import thunkMiddleware from "redux-thunk"
import { createLogger } from "redux-logger"

import rootReducer from "../reducers"

let createStoreWithMiddleware
if (process.env.NODE_ENV !== "production") {
  createStoreWithMiddleware = compose(
    applyMiddleware(thunkMiddleware, createLogger()),
    window.devToolsExtension ? window.devToolsExtension() : f => f
  )(createStore)
} else {
  createStoreWithMiddleware = compose(applyMiddleware(thunkMiddleware))(
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
