// @flow
import React from "react"
import sinon from "sinon"
import { assert } from "chai"
import { shallow } from "enzyme"

import RegisterEmailForm from "./RegisterEmailForm"

import { findFormikFieldByName } from "../../lib/test_utils"

describe("Register forms", () => {
  let sandbox, onSubmitStub

  beforeEach(() => {
    sandbox = sinon.createSandbox()
    onSubmitStub = sandbox.stub()
  })

  describe("RegisterEmailForm", () => {
    const renderForm = () =>
      shallow(<RegisterEmailForm onSubmit={onSubmitStub} />)

    it("passes onSubmit to Formik", () => {
      const wrapper = renderForm()

      assert.equal(wrapper.find("Formik").props().onSubmit, onSubmitStub)
    })

    it("renders the form", () => {
      const wrapper = renderForm()

      const form = wrapper.find("Formik").dive()
      assert.ok(findFormikFieldByName(form, "email").exists())
      assert.ok(form.find("button[type='submit']").exists())
    })
  })
})
