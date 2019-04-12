// @flow
import React from "react"
import { assert } from "chai"
import { shallow } from "enzyme"

import TopAppBar from "./TopAppBar"

import { routes } from "../lib/urls"
import { makeUser, makeAnonymousUser } from "../factories/user"

describe("TopAppBar component", () => {
  describe("for anonymous users", () => {
    const user = makeAnonymousUser()
    it("has a link to login", () => {
      assert.equal(
        shallow(<TopAppBar currentUser={user} />)
          .find("MixedLink")
          .at(0)
          .props().dest,
        routes.login
      )
    })

    it("has a link to register", () => {
      assert.equal(
        shallow(<TopAppBar currentUser={user} />)
          .find("MixedLink")
          .at(1)
          .props().dest,
        routes.register.begin
      )
    })
  })
  describe("for logged in users", () => {
    const user = makeUser()

    it("shows the logged in user", () => {
      assert.equal(
        shallow(<TopAppBar currentUser={user} />)
          .find(".user-name")
          .at(0)
          .text(),
        user.name
      )
    })

    it("has a link to logout", () => {
      assert.equal(
        shallow(<TopAppBar currentUser={user} />)
          .find(".link-section a")
          .at(0)
          .props().href,
        routes.logout
      )
    })
  })
})
