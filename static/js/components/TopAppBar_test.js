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

    it("has a button to collapse the menu", () => {
      assert.isOk(
        shallow(<TopAppBar currentUser={user} />)
          .find("button")
          .exists()
      )
    })
  })
  describe("for logged in users", () => {
    const user = makeUser()

    it("has a UserMenu component", () => {
      assert.isOk(
        shallow(<TopAppBar currentUser={user} />)
          .find("UserMenu")
          .exists()
      )
    })

    it("does not have a button to collapse the menu", () => {
      assert.isNotOk(
        shallow(<TopAppBar currentUser={user} />)
          .find("button")
          .exists()
      )
    })

    it("does not have MixedLink's for login/registration", () => {
      assert.isNotOk(
        shallow(<TopAppBar currentUser={user} />)
          .find("MixedLink")
          .exists()
      )
    })
  })
})
