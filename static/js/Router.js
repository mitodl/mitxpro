import React from "react"
import { Route, Router as ReactRouter } from "react-router"
import { Provider } from "react-redux"

import App from "./containers/App"
import withTracker from "./util/withTracker"
import ScrollToTop from "./components/ScrollToTop"

export default class Root extends React.Component {
  props: {
    history: Object,
    store: Store
  }

  render() {
    const { children, history, store } = this.props

    return (
      <div>
        <Provider store={store}>
          <ReactRouter history={history}>
            <ScrollToTop>{children}</ScrollToTop>
          </ReactRouter>
        </Provider>
      </div>
    )
  }
}

export const routes = <Route url="/" component={withTracker(App)} />
