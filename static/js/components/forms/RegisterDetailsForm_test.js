// @flow
import React from "react"
import sinon from "sinon"
import { assert } from "chai"
import { mount } from "enzyme"
import wait from "waait"

import RegisterDetailsForm from "./RegisterDetailsForm"

import {
  findFormikFieldByName,
  findFormikErrorByName
} from "../../lib/test_utils"

describe("RegisterDetailsForm", () => {
  let sandbox, onSubmitStub

  const countries = [
    {"code": "US", "name": "United States", "states": [{"code": "US-CO", "name": "Colorado"}, {"code": "US-MA", "name": "Massachusetts"}]},
    {"code": "CA", "name": "Canada", "states": [{"code": "CA-QC", "name": "Quebec"}, {"code": "CA-NS", "name": "Nova Scotia"}]},
    {"code": "FR", "name": "France", "states": []}
  ]

  const renderForm = () =>
    mount(<RegisterDetailsForm onSubmit={onSubmitStub} countries={countries}/>)

  beforeEach(() => {
    sandbox = sinon.createSandbox()
    onSubmitStub = sandbox.stub()
  })

  it("passes onSubmit to Formik", () => {
    const wrapper = renderForm()

    assert.equal(wrapper.find("Formik").props().onSubmit, onSubmitStub)
  })

  it("renders the form", () => {
    const wrapper = renderForm()

    const form = wrapper.find("Formik")
    assert.ok(findFormikFieldByName(form, "name").exists())
    assert.ok(findFormikFieldByName(form, "password").exists())
    assert.ok(form.find("button[type='submit']").exists())
  })

  //
  ;[
    ["password", "", "Password is a required field"],
    ["password", "pass", "Password must be at least 8 characters"],
    ["password", "passwor", "Password must be at least 8 characters"],
    ["password", "password", null],
    ["name", "", "Name is a required field"],
    ["name", "Jane", null]
  ].forEach(([name, value, errorMessage]) => {
    it(`validates the field name=${name}, value=${JSON.stringify(
      value
    )} and expects error=${JSON.stringify(errorMessage)}`, async () => {
      const wrapper = renderForm()

      const input = wrapper.find(`input[name="${name}"]`)
      input.simulate("change", { persist: () => {}, target: { name, value } })
      input.simulate("blur")
      await wait()
      wrapper.update()
      assert.deepEqual(
        findFormikErrorByName(wrapper, name).text(),
        errorMessage
      )
    })
  })
})
