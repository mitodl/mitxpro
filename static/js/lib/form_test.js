// @flow
import { assert } from "chai"

import { CYBERSOURCE_CHECKOUT_RESPONSE } from "./test_constants"
import { createForm } from "./form"

describe("form functions", () => {
  it("creates a form with hidden values corresponding to the payload", () => {
    const { url, payload } = CYBERSOURCE_CHECKOUT_RESPONSE
    const form = createForm(url, payload)

    const clone = { ...payload }
    for (const hidden of form.querySelectorAll("input[type=hidden]")) {
      const key = hidden.getAttribute("name")
      const value = hidden.getAttribute("value")
      // $FlowFixMe
      assert.equal(clone[key], value)
      // $FlowFixMe
      delete clone[key]
    }
    // all keys exhausted
    assert.deepEqual(clone, {})
    assert.equal(form.getAttribute("action"), url)
    assert.equal(form.getAttribute("method"), "post")
  })
})
