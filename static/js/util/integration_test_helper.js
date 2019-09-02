/* global SETTINGS: false */
import React from "react"
import R from "ramda"
import { shallow } from "enzyme"
import sinon from "sinon"
import { createMemoryHistory } from "history"

import configureStoreMain from "../store/configureStore"

import type { Sandbox } from "../flow/sinonTypes"
import * as networkInterfaceFuncs from "../store/network_interface"

export default class IntegrationTestHelper {
  sandbox: Sandbox
  browserHistory: History
  actions: Array<any>

  constructor() {
    this.sandbox = sinon.createSandbox({})
    this.actions = []

    this.scrollIntoViewStub = this.sandbox.stub()
    window.HTMLDivElement.prototype.scrollIntoView = this.scrollIntoViewStub
    window.HTMLFieldSetElement.prototype.scrollIntoView = this.scrollIntoViewStub
    this.browserHistory = createMemoryHistory()
    this.currentLocation = null
    this.browserHistory.listen(url => {
      this.currentLocation = url
    })

    const defaultResponse = {
      body:   {},
      status: 200
    }
    this.handleRequestStub = this.sandbox.stub().returns(defaultResponse)
    this.sandbox
      .stub(networkInterfaceFuncs, "makeRequest")
      .callsFake((url, method, options) => ({
        execute: callback => {
          const response = this.handleRequestStub(url, method, options)
          const err = null
          const resStatus = (response && response.status) || 0
          const resBody = (response && response.body) || undefined
          const resText = (response && response.text) || undefined
          const resHeaders = (response && response.header) || undefined

          callback(err, resStatus, resBody, resText, resHeaders)
        },
        abort: () => {
          throw new Error("Aborts currently unhandled")
        }
      }))
  }

  cleanup() {
    this.actions = []
    this.sandbox.restore()
  }

  configureHOCRenderer(
    WrappedComponent: Class<React.Component<*, *>>,
    InnerComponent: Class<React.Component<*, *>>,
    defaultState: Object,
    defaultProps = {}
  ) {
    const history = this.browserHistory
    return async (extraState = {}, extraProps = {}) => {
      const initialState = R.mergeDeepRight(defaultState, extraState)
      const store = configureStoreMain(initialState)
      const wrapper = await shallow(
        <WrappedComponent
          store={store}
          dispatch={store.dispatch}
          history={history}
          {...defaultProps}
          {...extraProps}
        />,
        {
          context: {
            // TODO: should be removed in the near future after upgrading enzyme
            store
          }
        }
      )

      // just a little convenience method
      store.getLastAction = function() {
        const actions = this.getActions()
        return actions[actions.length - 1]
      }

      // dive through layers of HOCs until we reach the desired inner component
      let inner = wrapper
      while (!inner.is(InnerComponent)) {
        // determine the type before we dive
        const cls = inner.type()
        if (InnerComponent === cls.WrappedComponent) {
          break
        }

        // shallow render this component
        inner = await inner.dive()

        // if it defines WrappedComponent, find() that so we skip over any intermediaries
        if (
          cls &&
          cls.hasOwnProperty("WrappedComponent") && // eslint-disable-line no-prototype-builtins
          inner.find(cls.WrappedComponent).length
        ) {
          inner = inner.find(cls.WrappedComponent)
        }
      }
      // one more time to shallow render the InnerComponent
      inner = await inner.dive()

      return { wrapper, inner, store }
    }
  }
}
