// @flow
import React from "react"
import sinon from "sinon"
import { assert } from "chai"
import { shallow } from "enzyme"
import { Formik } from "formik"

import ChangePasswordForm from "./ChangePasswordForm"

import { findFormikFieldByName } from "../../lib/test_utils"

import { makeUser } from "../../factories/user"

describe("ChangePasswordForm", () => {
  let sandbox, onSubmitStub

  const user = makeUser()

  const renderForm = () =>
    shallow(<ChangePasswordForm onSubmit={onSubmitStub} user={user} />)

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
    assert.ok(findFormikFieldByName(form, "email").exists())
    assert.ok(findFormikFieldByName(form, "oldPassword").exists())
    assert.ok(findFormikFieldByName(form, "newPassword").exists())
    assert.ok(findFormikFieldByName(form, "confirmPassword").exists())
    assert.ok(form.find("button[type='submit']").exists())
  })

  it("old password is required to change the email address", async () => {
    const wrapper = renderForm()
    try {
      await wrapper.find(Formik).prop("validate")({
        email:         "abc@example.com",
        emailPassword: ""
      })
    } catch (errors) {
      assert.equal(errors.emailPassword, "Confirm Password is a required field")
    }
  })
})
