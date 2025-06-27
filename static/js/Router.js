import React from "react"
import { BrowserRouter, Route } from "react-router-dom"
import { Provider } from "react-redux"

import App from "./containers/App"
import withTracker from "./util/withTracker"
import ScrollToTop from "./components/ScrollToTop"

const TrackedApp = withTracker(App);

export default class Root extends React.Component {
  props: {
    store: Store
  }

  render() {
    const { children, store } = this.props

    return (
      <div>
        <Provider store={store}>
          <BrowserRouter>
            <ScrollToTop>{children}</ScrollToTop>
          </BrowserRouter>
        </Provider>
      </div>
    )
  }
}

export const routes = <Route url="/" element={<TrackedApp />} />
