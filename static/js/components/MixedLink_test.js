// @flow
import React from "react"
import { assert } from "chai"
import { shallow } from "enzyme"
import { MemoryRouter } from "react-router-dom"

import MixedLink from "./MixedLink"
import { SPA_APP_CONTEXT, MIXED_APP_CONTEXT } from "../contextDefinitions"
import { getComponentWithContext } from "../lib/test_utils"

describe("MixedLink component", () => {
  const testDest = "/some/url",
    testLinkText = "link",
    testAriaLabel = "aria link"

  const renderMixedLink = (appType, props) => {
    const { inner } = getComponentWithContext(MixedLink, props, appType)
    // Render with MemoryRouter to support <Link> components
    return shallow(<MemoryRouter>{inner}</MemoryRouter>)
  }

  it(`renders a react router Link when the app type is '${SPA_APP_CONTEXT}'`, () => {
    const wrapper = renderMixedLink(SPA_APP_CONTEXT, {
      dest:         testDest,
      children:     testLinkText,
      "aria-label": testAriaLabel
    })

    const link = wrapper.find("Link")

    assert.isTrue(link.exists())
    const linkProps = link.props()
    assert.equal(linkProps.to, testDest)
    assert.equal(linkProps.children, testLinkText)
    assert.equal(linkProps["aria-label"], testAriaLabel)
  })

  it(`renders a normal anchor link when the app type is '${MIXED_APP_CONTEXT}'`, () => {
    const wrapper = renderMixedLink(MIXED_APP_CONTEXT, {
      dest:         testDest,
      children:     testLinkText,
      "aria-label": testAriaLabel
    })

    const link = wrapper.find("a")

    assert.isTrue(link.exists())
    const linkProps = link.props()
    assert.equal(linkProps.href, testDest)
    assert.equal(linkProps.children, testLinkText)
    assert.equal(linkProps["aria-label"], testAriaLabel)
  })
})
