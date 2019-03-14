// @flow
import React from "react"
import { Switch, Route } from "react-router"
import urljoin from "url-join"

import { routes } from "../lib/urls"

import Header from "../components/Header"

import HomePage from "./pages/HomePage"
import LoginPage from "./pages/LoginPage"

import type { Match } from "react-router"

type Props = {
  match: Match
}

export default class App extends React.Component<Props, void> {
  render() {
    const { match } = this.props
    return (
      <div className="app">
        <Header />
        <Switch>
          <Route
            exact
            path={`${match.url}${routes.home}`}
            component={HomePage}
          />
          <Route
            path={urljoin(match.url, String(routes.login))}
            component={LoginPage}
          />
        </Switch>
      </div>
    )
  }
}
