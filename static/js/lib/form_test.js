// @flow
import { assert } from "chai"
import { shallow } from "enzyme"

import { CYBERSOURCE_CHECKOUT_RESPONSE } from "./test_constants"
import { createCyberSourceForm, formatErrors } from "./form"

describe("form functions", () => {
  it("creates a form with hidden values corresponding to the payload", () => {
    const { url, payload } = CYBERSOURCE_CHECKOUT_RESPONSE
    const form = createCyberSourceForm(url, payload)

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

  describe("formatErrors", () => {
    it("should return null if there is no error", () => {
      assert.isNull(formatErrors(null))
    })

    it("should return a div with the error string if the error is a string", () => {
      const wrapper = shallow(formatErrors("error"))
      assert.equal(wrapper.find(".error").text(), "error")
    })

    it("should return the first item in the error if there is no 'items'", () => {
      const error = ["error"]
      const wrapper = shallow(formatErrors(error))
      assert.equal(wrapper.find(".error").text(), "error")
    })
  })
})
