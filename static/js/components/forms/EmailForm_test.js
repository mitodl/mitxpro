// @flow
import React from "react"
import sinon from "sinon"
import { assert } from "chai"
import { shallow } from "enzyme"

import EmailForm from "./EmailForm"

import { findFormikFieldByName } from "../../lib/test_utils"

describe("EmailForm", () => {
  let sandbox, onSubmitStub

  const renderForm = () => shallow(<EmailForm onSubmit={onSubmitStub} />)

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

    const form = wrapper.find("Formik").dive()
    const emailField = findFormikFieldByName(form, "email")
    assert.ok(emailField.exists())
    assert.equal(emailField.prop("autoComplete"), "email")
    assert.ok(form.find("button[type='submit']").exists())
  })
})
