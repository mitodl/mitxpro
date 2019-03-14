// @flow
import React from "react"
import { assert } from "chai"
import { shallow } from "enzyme"

import HomePage from "./HomePage"

describe("HomePage", () => {
  it("displays the app name", () => {
    assert.equal(shallow(<HomePage />).text(), "MIT xPro Home")
  })
})
