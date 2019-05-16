// @flow
import React from "react"

import { routes } from "../lib/urls"
import MixedLink from "./MixedLink"

import type { CurrentUser } from "../flow/authTypes"

type Props = {
  currentUser: CurrentUser
}

const TopAppBar = ({ currentUser }: Props) => (
  <header className="header-holder">
    <div className="container">
      <nav className="sub-nav navbar navbar-expand-md link-section">
        <a href={routes.root} className="navbar-brand">
          <img
            src="/static/images/mitx-pro-logo.png"
            className="site-logo"
            alt="MIT xPRO"
          />
        </a>
        <button
          className="navbar-toggler nav-opener"
          type="button"
          data-toggle="collapse"
          data-target="#nav"
          aria-controls="nav"
          aria-expanded="false"
          aria-label="Toggle navigation"
        >
          <span className="navbar-toggler-icon" />
          Menu
        </button>
        <ul
          id="nav"
          className="collapse navbar-collapse px-0 justify-content-end"
        >
          <li>
            <a href={routes.catalog} className="" aria-label="catalog">
              Catalog
            </a>
          </li>
          {currentUser.is_authenticated ? (
            <React.Fragment>
              <li>
                <strong className="dashboard-link">
                  <MixedLink
                    dest={routes.dashboard}
                    aria-label="Dashboard link"
                  >
                    Dashboard
                  </MixedLink>
                </strong>
              </li>
              <li>
                <a href={routes.logout} className="button" aria-label="Log Out">
                  Sign Out
                </a>
              </li>
            </React.Fragment>
          ) : (
            <React.Fragment>
              <li>
                <MixedLink
                  dest={routes.login.begin}
                  className="button"
                  aria-label="Login"
                >
                  Sign In
                </MixedLink>
              </li>
              <li>
                <MixedLink
                  dest={routes.register.begin}
                  className="button"
                  aria-label="Login"
                >
                  Create Account
                </MixedLink>
              </li>
            </React.Fragment>
          )}
        </ul>
      </nav>
    </div>
  </header>
)

export default TopAppBar
