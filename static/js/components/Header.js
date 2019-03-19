// @flow
import React from "react"

import { Link } from "react-router-dom"

import { routes } from "../lib/urls"

const Header = () => (
  <div>
    <ul>
      <li>
        <Link to={routes.login}>Login</Link>
      </li>
      <li>
        <Link to={routes.register.begin}>Register</Link>
      </li>
    </ul>
  </div>
)

export default Header
