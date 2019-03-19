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
        .at(0)
        .props().to,
      routes.login
    )
  })

  it("has a link to register", () => {
    assert.equal(
      shallow(<Header />)
        .find("Link")
        .at(1)
        .props().to,
      routes.register.begin
    )
  })
})
