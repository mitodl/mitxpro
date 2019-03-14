// @flow
import React from "react"
import sinon from "sinon"
import { assert } from "chai"
import { shallow } from "enzyme"

import { LoginEmailForm, LoginPasswordForm } from "./login"

describe("Login forms", () => {
  let sandbox, onSubmitStub

  beforeEach(() => {
    sandbox = sinon.createSandbox()
    onSubmitStub = sandbox.stub()
  })

  describe("LoginEmailForm", () => {
    const renderForm = () => shallow(<LoginEmailForm onSubmit={onSubmitStub} />)

    it("passes onSubmit to Formik", () => {
      const wrapper = renderForm()

      assert.equal(wrapper.find("Formik").props().onSubmit, onSubmitStub)
    })

    it("renders the form", () => {
      const wrapper = renderForm()

      const form = wrapper.find("Formik").dive()
      assert.ok(
        form
          .find("FormikConnect(FieldInner)")
          .filterWhere(node => node.prop("name") === "email")
          .exists()
      )
      assert.ok(form.find("button[type='submit']").exists())
    })
  })

  describe("LoginPasswordForm", () => {
    const renderForm = () =>
      shallow(<LoginPasswordForm onSubmit={onSubmitStub} />)

    it("passes onSubmit to Formik", () => {
      const wrapper = renderForm()

      assert.equal(wrapper.find("Formik").props().onSubmit, onSubmitStub)
    })

    it("renders the form", () => {
      const wrapper = renderForm()

      const form = wrapper.find("Formik").dive()
      assert.ok(
        form
          .find("FormikConnect(FieldInner)")
          .filterWhere(node => node.prop("name") === "password")
          .exists()
      )
      assert.ok(form.find("button[type='submit']").exists())
    })
  })
})
