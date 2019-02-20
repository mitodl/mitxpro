/* global SETTINGS: false */
import React from "react"
import { mount } from "enzyme"
import sinon from "sinon"
import { createMemoryHistory } from "history"
import configureTestStore from "redux-asserts"

import Router, { routes } from "../Router"
import rootReducer from "../reducers"
import type { Action } from "../flow/reduxTypes"
import type { TestStore } from "../flow/reduxTypes"
import type { Sandbox } from "../flow/sinonTypes"

export default class IntegrationTestHelper {
  listenForActions: (a: Array<string>, f: Function) => Promise<*>
  dispatchThen: (a: Action) => Promise<*>
  sandbox: Sandbox
  store: TestStore
  browserHistory: History

  constructor() {
    this.sandbox = sinon.createSandbox({})
    this.store = configureTestStore((...args) => {
      // uncomment to listen on dispatched actions
      // console.log(args);
      return rootReducer(...args)
    })

    this.listenForActions = this.store.createListenForActions()
    this.dispatchThen = this.store.createDispatchThen()

    this.scrollIntoViewStub = this.sandbox.stub()
    window.HTMLDivElement.prototype.scrollIntoView = this.scrollIntoViewStub
    window.HTMLFieldSetElement.prototype.scrollIntoView = this.scrollIntoViewStub
    this.browserHistory = createMemoryHistory()
    this.currentLocation = null
    this.browserHistory.listen(url => {
      this.currentLocation = url
    })
  }

  cleanup() {
    this.sandbox.restore()
  }

  /**
   * Renders the components using the given URL.
   * @param url {String} The react-router URL
   * @param typesToAssert {Array<String>|null} A list of redux actions to listen for.
   * If null, actions types for the success case is assumed.
   * @returns {Promise<*>} A promise which provides [wrapper, div] on success
   */
  renderComponent(
    url: string = "/",
    typesToAssert: Array<string> | null = null
  ): Promise<*> {
    let expectedTypes = []
    if (typesToAssert === null) {
      expectedTypes = []
    } else {
      expectedTypes = typesToAssert
    }

    let wrapper, div

    return this.listenForActions(expectedTypes, () => {
      this.browserHistory.push(url)
      div = document.createElement("div")
      div.setAttribute("id", "integration_test_div")
      document.body.appendChild(div)
      wrapper = mount(
        <div>
          <Router history={this.browserHistory} store={this.store}>
            {routes}
          </Router>
        </div>,
        {
          attachTo: div
        }
      )
    }).then(() => {
      return Promise.resolve([wrapper, div])
    })
  }
}
