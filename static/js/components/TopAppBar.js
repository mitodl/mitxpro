// @flow
/* global SETTINGS: false */
import React from "react"

import { routes } from "../lib/urls"
import MixedLink from "./MixedLink"
import UserMenu from "./UserMenu"
import type { Location } from "react-router"

import type { CurrentUser } from "../flow/authTypes"

type Props = {
  currentUser: CurrentUser,
  location: ?Location
}

const shouldShowLoginSignup = location =>
  !location ||
  !(
    location.pathname === routes.ecommerceBulk.bulkPurchase ||
    location.pathname === routes.ecommerceBulk.receipt
  )

const TopAppBar = ({ currentUser, location }: Props) => (
  <header className="header-holder">
    <div className="container">
      <nav
        className={`sub-nav navbar navbar-expand-md link-section ${
          currentUser.is_authenticated ? "nowrap login" : ""
        }`}
      >
        <div className="navbar-brand">
          <a
            href="https://web.mit.edu/"
            rel="noopener noreferrer"
            target="_blank"
            className="mit-link"
          />
          <a href={routes.root} className="xpro-link" />
          <img
            src="/static/images/mitx-pro-logo.png"
            className="site-logo"
            alt={SETTINGS.site_name}
            width={154}
            height={47.5}
          />
        </div>
        {currentUser.is_authenticated ? null : (
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
        )}
        <ul
          id="nav"
          className={`${
            currentUser.is_authenticated ? "" : "collapse"
          } navbar-collapse px-0 justify-content-end`}
        >
          <li>
            <a href={routes.catalog} className="" aria-label="catalog">
              Catalog
            </a>
          </li>
          {shouldShowLoginSignup(location) ? (
            currentUser.is_authenticated ? (
              <li>
                <UserMenu currentUser={currentUser} />
              </li>
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
            )
          ) : null}
        </ul>
      </nav>
    </div>
  </header>
)

export default TopAppBar
