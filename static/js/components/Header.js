// @flow
import React from "react"

import { Link } from "react-router-dom"

import { routes } from "../lib/urls"

import type { CurrentUser } from "../flow/authTypes"

type Props = {
  currentUser: CurrentUser
}

const Header = ({ currentUser }: Props) => (
  <div>
    <ul>
      {currentUser && currentUser.is_authenticated ? (
        <React.Fragment>
          <li>Logged in as {currentUser.name}</li>
          <li>
            <a href={routes.logout}>Logout</a>
          </li>
        </React.Fragment>
      ) : (
        <React.Fragment>
          <li>
            <Link to={routes.login.begin}>Login</Link>
          </li>
          <li>
            <Link to={routes.register.begin}>Register</Link>
          </li>
        </React.Fragment>
      )}
    </ul>
  </div>
)

export default Header
