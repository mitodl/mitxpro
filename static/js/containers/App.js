// @flow
import React from "react"
import { Route } from "react-router"
import type { Match } from "react-router"

import CourseDashboardPage from "./CourseDashboardPage"

export default class App extends React.Component<*, void> {
  props: {
    match: Match
  }

  render() {
    return (
      <div className="app">
        <Route exact path="/" component={CourseDashboardPage} />
      </div>
    )
  }
}
