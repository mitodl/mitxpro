// @flow
import React from "react"
import sinon from "sinon"
import { shallow } from "enzyme"
import { assert } from "chai"

import Expandable from "./Expandable"

import { shouldIf } from "../lib/test_utils"

describe("Expandable", () => {
  let sandbox

  beforeEach(() => {
    sandbox = sinon.createSandbox()
  })

  afterEach(() => {
    sandbox.restore()
  })

  it("should toggle the explanation text", () => {
    const title = "title"
    const children = "children"
    const wrapper = shallow(<Expandable title={title}>{children}</Expandable>)

    assert.isFalse(wrapper.state().expanded)
    wrapper.find(".header").prop("onClick")()
    assert.isTrue(wrapper.state().expanded)
    wrapper.find(".header").prop("onClick")()
    assert.isFalse(wrapper.state().expanded)
  })

  //
  ;[true, false].forEach(expanded => {
    it(`${shouldIf(expanded)} render the explanation text`, () => {
      const title = "title"
      const children = "children"
      const wrapper = shallow(<Expandable title={title}>{children}</Expandable>)
      wrapper.setState({ expanded })
      assert.equal(wrapper.find(".body").text(), expanded ? children : "")
    })
  })
})
