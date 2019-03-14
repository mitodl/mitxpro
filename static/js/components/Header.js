// @flow
import React from "react"

import { Link } from "react-router-dom"

import { routes } from "../lib/urls"

const Header = () => (
  <div>
    <Link to={routes.login}>Login</Link>
  </div>
)

export default Header
