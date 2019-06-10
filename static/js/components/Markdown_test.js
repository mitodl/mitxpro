// @flow
import React from "react"
import { mount } from "enzyme"
import { assert } from "chai"

import Markdown from "./Markdown"

describe("Markdown", () => {
  const render = source => mount(<Markdown source={source} />)

  it("should render markdown", () => {
    const wrapper = render("# MARKDOWN\n\nyeah markdown")
    assert.equal(wrapper.find("ReactMarkdown").props().className, "markdown")
    assert.equal(wrapper.find("h1").text(), "MARKDOWN")
    assert.equal(wrapper.text(), "MARKDOWNyeah markdown")
  })

  it("should not render images", () => {
    const wrapper = render(
      "![](https://upload.wikimedia.org/wikipedia/commons/4/4c/Chihuahua1_bvdb.jpg)"
    )
    assert.isNotOk(wrapper.find("img").exists())
  })

  it("shouldnt turn non-url brackets into links", () => {
    const wrapper = render("just [bracket] stuff")
    assert.isNotOk(wrapper.find("a").exists())
  })
})
