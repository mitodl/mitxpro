// @flow
import React from "react"
import sinon from "sinon"
import { assert } from "chai"
import { shallow } from "enzyme"

import LoginPasswordForm from "./LoginPasswordForm"

import { findFormikFieldByName } from "../../lib/test_utils"

describe("LoginPasswordForm", () => {
  let sandbox, onSubmitStub

  const renderForm = () =>
    shallow(<LoginPasswordForm onSubmit={onSubmitStub} />)

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
    assert.ok(findFormikFieldByName(form, "password").exists())
    assert.ok(form.find("button[type='submit']").exists())
  })
})
