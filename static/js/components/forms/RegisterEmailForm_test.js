// @flow
/* global SETTINGS: false */
import React from "react"
import sinon from "sinon"
import { assert } from "chai"
import { shallow } from "enzyme"

import RegisterEmailForm from "./RegisterEmailForm"

import { findFormikFieldByName } from "../../lib/test_utils"

describe("Register forms", () => {
  let sandbox, onSubmitStub

  beforeEach(() => {
    SETTINGS.recaptchaKey = null
    sandbox = sinon.createSandbox()
    onSubmitStub = sandbox.stub()
  })

  describe("RegisterEmailForm", () => {
    const renderForm = () => {
      const wrapper = shallow(<RegisterEmailForm onSubmit={onSubmitStub} />)
      return {
        wrapper,
        form: wrapper.find("Formik").dive()
      }
    }

    it("passes onSubmit to Formik", () => {
      const { wrapper } = renderForm()

      assert.equal(wrapper.find("Formik").props().onSubmit, onSubmitStub)
    })

    it("renders the form", () => {
      const { form } = renderForm()
      const emailField = findFormikFieldByName(form, "email")

      assert.ok(emailField.exists())
      assert.equal(emailField.prop("autoComplete"), "email")
      assert.isOk(form.find("button[type='submit']").exists())
    })

    it("includes a recaptch if enabled", () => {
      SETTINGS.recaptchaKey = "abc"
      const { form } = renderForm()

      assert.isOk(form.find("ScaledRecaptcha").exists())
    })

    it("doesn't include a recaptch if disabled", () => {
      const { form } = renderForm()

      assert.isNotOk(form.find("ScaledRecaptcha").exists())
    })
  })
})
