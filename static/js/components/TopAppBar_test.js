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
          .prop("dest"),
        routes.login
      )
    })

    it("has a link to register", () => {
      assert.equal(
        shallow(<TopAppBar currentUser={user} />)
          .find("MixedLink")
          .at(1)
          .prop("dest"),
        routes.register.begin
      )
    })
  })
  describe("for logged in users", () => {
    const user = makeUser()

    it("shows a link to the user dashboard", () => {
      const dashLink = shallow(<TopAppBar currentUser={user} />)
        .find(".dashboard-link")
        .at(0)
        .find("MixedLink")
        .at(0)
      assert.equal(dashLink.prop("children"), "Dashboard")
      assert.equal(dashLink.prop("dest"), routes.dashboard)
    })

    it("has a link to logout", () => {
      assert.equal(
        shallow(<TopAppBar currentUser={user} />)
          .find(".link-section a")
          .at(0)
          .prop("href"),
        routes.logout
      )
    })
  })
})
