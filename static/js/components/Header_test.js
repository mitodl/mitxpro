// @flow
import React from "react"
import { assert } from "chai"
import { shallow } from "enzyme"

import Header from "./Header"

import { routes } from "../lib/urls"
import { makeUser, makeAnonymousUser } from "../factories/user"

describe("Header component", () => {
  describe("for anonymous users", () => {
    const user = makeAnonymousUser()
    it("has a link to login", () => {
      assert.equal(
        shallow(<Header currentUser={user} />)
          .find("Link")
          .at(0)
          .props().to,
        routes.login
      )
    })

    it("has a link to register", () => {
      assert.equal(
        shallow(<Header currentUser={user} />)
          .find("Link")
          .at(1)
          .props().to,
        routes.register.begin
      )
    })
  })
  describe("for logged in users", () => {
    const user = makeUser()

    it("shows the logged in user", () => {
      assert.equal(
        shallow(<Header currentUser={user} />)
          .find("li")
          .at(0)
          .text(),
        `Logged in as ${user.name}`
      )
    })

    it("has a link to logout", () => {
      assert.equal(
        shallow(<Header currentUser={user} />)
          .find("a")
          .at(0)
          .props().href,
        routes.logout
      )
    })
  })
})
