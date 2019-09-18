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
import { makeCountries } from "../../factories/user"

describe("RegisterDetailsForm", () => {
  let sandbox, onSubmitStub

  const countries = makeCountries()

  const renderForm = () =>
    mount(<RegisterDetailsForm onSubmit={onSubmitStub} countries={countries} />)

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
    ["password", "password123", null],
    [
      "password",
      "password",
      "Password must contain at least one letter and number"
    ],
    ["name", "", "Full Name is a required field"],
    ["name", "  ", "Full Name is a required field"],
    ["name", "Jane", null],
    ["legal_address.city", "Cambridge", null],
    ["legal_address.city", "", "City is a required field"],
    ["legal_address.city", "  ", "City is a required field"]
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

  //
  ;[["US", "FR"], ["CA", "GB"]].forEach(([countryState, countryNoState]) => {
    it(`validates that state & postal_code required for ${countryState} but not ${countryNoState}`, async () => {
      const wrapper = renderForm()
      // Select country requiring state and zipcode
      const country = wrapper.find(`select[name="legal_address.country"]`)
      country.simulate("change", {
        persist: () => {},
        target:  { name: "legal_address.country", value: countryState }
      })
      country.simulate("blur")
      await wait()
      wrapper.update()
      const stateTerritory = wrapper.find(
        `select[name="legal_address.state_or_territory"]`
      )
      assert.isTrue(stateTerritory.exists())
      stateTerritory.simulate("change", {
        persist: () => {},
        target:  { name: "legal_address.state_or_territory", value: "" }
      })
      stateTerritory.simulate("blur")
      await wait()
      wrapper.update()
      const postalCode = wrapper.find(`input[name="legal_address.postal_code"]`)
      assert.isTrue(postalCode.exists())
      postalCode.simulate("change", {
        persist: () => {},
        target:  { name: "legal_address.postalCode", value: "" }
      })
      postalCode.simulate("blur")
      await wait()
      wrapper.update()
      assert.deepEqual(
        findFormikErrorByName(
          wrapper,
          "legal_address.state_or_territory"
        ).text(),
        "State/Territory is a required field"
      )
      assert.deepEqual(
        findFormikErrorByName(wrapper, "legal_address.postal_code").text(),
        countryState === "US"
          ? "Postal Code must be formatted as either 'NNNNN' or 'NNNNN-NNNN'"
          : "Postal Code must be formatted as 'ANA NAN'"
      )

      // Select country not requiring state and zipcode
      country.simulate("change", {
        persist: () => {},
        target:  { name: "legal_address.country", value: countryNoState }
      })
      country.simulate("blur")
      await wait()
      wrapper.update()
      assert.isFalse(
        findFormikErrorByName(
          wrapper,
          "legal_address.state_or_territory"
        ).exists()
      )
      assert.isFalse(
        findFormikErrorByName(wrapper, "legal_address.postal_code").exists()
      )
    })
  })

  it(`validates that additional street address lines are created on request`, async () => {
    const wrapper = renderForm()
    assert.isTrue(
      wrapper.find(`input[name="legal_address.street_address[1]"]`).exists()
    )
    assert.isFalse(
      wrapper.find(`input[name="legal_address.street_address[2]"]`).exists()
    )
    const moreStreets = wrapper.find(".additional-street")
    moreStreets.simulate("click")
    assert.isTrue(
      wrapper.find(`input[name="legal_address.street_address[2]"]`).exists()
    )
    moreStreets.simulate("click")
    assert.isTrue(
      wrapper.find(`input[name="legal_address.street_address[3]"]`).exists()
    )
    assert.isFalse(wrapper.find(".additional-street").exists())
  })

  it(`validates that street address[0] is required`, async () => {
    const wrapper = renderForm()
    const street = wrapper.find(`input[name="legal_address.street_address[0]"]`)
    street.simulate("change", {
      persist: () => {},
      target:  { name: "legal_address.street_address[0]", value: "" }
    })
    street.simulate("blur")
    await wait()
    wrapper.update()
    assert.deepEqual(
      findFormikErrorByName(wrapper, "legal_address.street_address").text(),
      "Street address is a required field"
    )
  })

  //
  ;[
    ["name", "name"],
    ["legal_address.first_name", "given-name"],
    ["legal_address.last_name", "family-name"],
    ["legal_address.street_address[0]", "address-line1"],
    ["legal_address.country", "country"],
    ["legal_address.city", "address-level2"]
  ].forEach(([formFieldName, autoCompleteName]) => {
    it(`validates that autoComplete=${autoCompleteName}  for field ${formFieldName}`, async () => {
      const wrapper = renderForm()
      const form = wrapper.find("Formik")
      assert.equal(
        findFormikFieldByName(form, formFieldName).prop("autoComplete"),
        autoCompleteName
      )
    })
  })
})
