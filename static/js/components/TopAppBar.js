// @flow
import React from "react"

import { routes } from "../lib/urls"
import MixedLink from "./MixedLink"

import type { CurrentUser } from "../flow/authTypes"

type Props = {
  currentUser: CurrentUser
}

const TopAppBar = ({ currentUser }: Props) => (
  <header className="mdc-top-app-bar">
    <div className="mdc-top-app-bar__row">
      <section className="mdc-top-app-bar__section mdc-top-app-bar__section--align-start logo-section">
        <a href={routes.root}>
          <img
            src="/static/images/mitx-pro-logo.png"
            className="site-logo"
            alt="MIT xPRO"
          />
        </a>
      </section>
      <section className="mdc-top-app-bar__section mdc-top-app-bar__section--align-end link-section">
        {currentUser.is_authenticated ? (
          <React.Fragment>
            <strong className="user-name">{currentUser.name}</strong>
            <a
              href={routes.logout}
              className="link-button"
              aria-label="Log Out"
            >
              Log Out
            </a>
          </React.Fragment>
        ) : (
          <React.Fragment>
            <MixedLink
              dest={routes.login.begin}
              className="link-button"
              aria-label="Login"
            >
              Login
            </MixedLink>
            <MixedLink
              dest={routes.register.begin}
              className="link-button"
              aria-label="Login"
            >
              Register
            </MixedLink>
          </React.Fragment>
        )}
      </section>
    </div>
  </header>
)

export default TopAppBar
