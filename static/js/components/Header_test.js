// @flow
import React from "react"
import { assert } from "chai"
import { shallow } from "enzyme"

import Header from "./Header"

import { routes } from "../lib/urls"

describe("Header component", () => {
  it("has a link to login", () => {
    assert.equal(
      shallow(<Header />)
        .find("Link")
        .props().to,
      routes.login
    )
  })
})
