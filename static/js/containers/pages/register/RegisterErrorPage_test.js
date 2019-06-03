// @flow
/* global SETTINGS: false */
import React from "react"
import { assert } from "chai"
import { shallow } from "enzyme"

import RegisterErrorPage from "./RegisterErrorPage"

describe("RegisterErrorPage", () => {
  const renderPage = () => shallow(<RegisterErrorPage />)

  it("displays a link to email support", async () => {
    const email = "email@localhost"
    SETTINGS.support_email = email
    const wrapper = await renderPage()

    assert.equal(wrapper.find("a").prop("href"), `mailto:${email}`)
  })
})
