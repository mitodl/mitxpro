/* global SETTINGS: false */
import React from "react"
import {mergeDeepRight, isUndefined} from "ramda"
import { shallow } from "enzyme"
import sinon from "sinon"
import { Router } from "react-router-dom"
import { createMemoryHistory } from "history"

import configureStoreMain from "../store/configureStore"

import type { Sandbox } from "../flow/sinonTypes"
import * as networkInterfaceFuncs from "../store/network_interface"


type RendererState = { [string]: any }
type RendererProps = { [string]: any }

type RendererConfig = {
  WrappedComponent: Class<React.Component<*, *>>,
  InnerComponent: ?Class<React.Component<*, *>>,
  history: History,
  useRouter: boolean,
  defaultState: RendererState,
  defaultProps: RendererProps
}

const rendererDefaults: RendererConfig = {
  wrappedComponent: undefined,
  innerComponent: undefined,
  history: undefined,
  useRouter: false,
  state: {},
  props: {}
}

const createHistory = (historyConfig: ?any) => {
  return createMemoryHistory(historyConfig || {})
}

const createStore = (state: any) => {
  const store = configureStoreMain(state)
  // just a little convenience method
  store.getLastAction = function() {
    const actions = this.getActions()
    return actions[actions.length - 1]
  }
  return store
}

const findInnerComponent = async (wrapper: any, InnerComponent: Class<React.Component<*, *>>) => {
  // dive through layers of HOCs until we reach the desired inner component
  let inner = wrapper
  while (!inner.is(InnerComponent)) {
    // determine the type before we dive
    const cls = inner.type()
    if (
      cls &&
      cls.hasOwnProperty("WrappedComponent") &&
      InnerComponent === cls.WrappedComponent) {
      break
    }

    // shallow render this component
    inner = await inner.dive()

    // if it defines WrappedComponent, find() that so we skip over any intermediaries
    if (
      cls &&
      cls.hasOwnProperty("WrappedComponent") &&
      inner.find(cls.WrappedComponent).length
    ) {
      inner = inner.find(cls.WrappedComponent)
    }
  }
  console.log(inner.type())
  // one more time to shallow render the InnerComponent
  inner = await inner.dive()

  return inner
}

class ComponentRenderer {
  constructor(config: ?RendererConfig) {
    this.config = {
      ...rendererDefaults,
      ...(config || {})
    }
  }

  withHistory(newHistory: ?History) {
    const { history, ...config} = this.config
    return new ComponentRenderer({
      ...config,
      history: newHistory || history || this.createHistory()
    })
  }

  withConfiguredHistory(historyConfig: any) {
    return new ComponentRenderer({
      ...this.config,
      history: createHistory(historyConfig),
    })
  }

  withInnerComponent(InnerComponent: Class<React.Component<*, *>>) {
      return new ComponentRenderer({
        ...this.config,
        InnerComponent
      })
  }

  withRouter() {
    const { history, ...config} = this.config
    return new ComponentRenderer({
      ...config,
      history: history || this.createHistory(),
      useRouter: true,
    })
  }

  withState(newState: RendererState) {
      const {state, ...config} = this.config
      return new ComponentRenderer({
        ...config,
        state: mergeDeepRight(state, newState)
      })
  }

  withProps(newProps: RendererProps) {
      const {props, ...config} = this.config
      return new ComponentRenderer({
        ...config,
        props: mergeDeepRight(props, newProps)
      })
  }

  async render() {
    const { WrappedComponent, InnerComponent, history, useRouter, props, state } = this.config

    const store = createStore(state)

    let component = (
      <WrappedComponent
        store={store}
        dispatch={store.dispatch}
        {...props}
      />
    )

    if (useRouter) {
      component = (
        <Router history={history}>
          {compoment}
        </Router>
      )
    }

    let wrapper = await shallow(
      component,
      {
        context: {
          // TODO: should be removed in the near future after upgrading enzyme
          store
        }
      }
    )

    const inner = !isUndefined(InnerComponent) ? findInnerComponent(wrapper, InnerComponent) : null

    // return a smart object that raises errors if you try to access things you didn't configure
    return {
      wrapper,
      store,
      get inner() {
        if (!inner) {
          throw Error("Renderer is not configured with an InnerComponent, call withInnerComponent()")
        }
        return inner
      },
      get history() {
        if (!history) {
          throw Error("Renderer is not configured with history, call one of withHistory(), withConfiguredHistory(), or withRouter()")
        }
        return history
      }
    }

  }
}

export const createComponentRenderer = (WrappedComponent: Class<React.Component<*, *>>) => (
  new ComponentRenderer({ WrappedComponent })
)


export default class IntegrationTestHelper {
  sandbox: Sandbox
  browserHistory: History

  constructor() {
    this.sandbox = sinon.createSandbox({})

    this.scrollIntoViewStub = this.sandbox.stub()
    window.HTMLDivElement.prototype.scrollIntoView = this.scrollIntoViewStub
    window.HTMLFieldSetElement.prototype.scrollIntoView = this.scrollIntoViewStub

    this.currentLocation = null
    this.browserHistory = createMemoryHistory()
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
    this.sandbox.restore()
  }

  configureHOCRenderer(
    WrappedComponent: Class<React.Component<*, *>>,
    InnerComponent: Class<React.Component<*, *>>,
    defaultState: Object,
    defaultProps = {}
  ) {
    const history = this.browserHistory
    return async (
      extraState = {},
      extraProps = {}
    ) => {
      const initialState = mergeDeepRight(defaultState, extraState)
      const store = createStore(initialState)

      let wrapper = await shallow(
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

      const inner = findInnerComponent(wrapper, InnerComponent)

      return { wrapper, inner, store }
    }
  }
}
