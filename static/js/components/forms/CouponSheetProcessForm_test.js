// @flow
import React from "react";
import sinon from "sinon";
import { assert } from "chai";
import { mount } from "enzyme";
import wait from "waait";

import { CouponSheetProcessForm } from "./CouponSheetProcessForm";

import {
  findFormikFieldByName,
  findFormikErrorByName,
} from "../../lib/test_utils";

import { SHEET_IDENTIFIER_ID, SHEET_IDENTIFIER_TITLE } from "../../constants";

describe("CouponSheetProcessForm", () => {
  let sandbox, onSubmitStub;

  const renderForm = () =>
    mount(<CouponSheetProcessForm onSubmit={onSubmitStub} />);

  beforeEach(() => {
    sandbox = sinon.createSandbox();
    onSubmitStub = sandbox.stub();
  });

  it("passes onSubmit to Formik", () => {
    const wrapper = renderForm();
    assert.equal(wrapper.find("Formik").props().onSubmit, onSubmitStub);
  });

  it("renders the form", () => {
    const wrapper = renderForm();
    const form = wrapper.find("Formik");
    assert.ok(findFormikFieldByName(form, "sheet_identifier_value").exists());
    assert.ok(form.find("button[type='submit']").exists());
  });

  [
    // Sheet Title validation (allows spaces)
    ["sheet_identifier_value", "", "Sheet Title is required", SHEET_IDENTIFIER_TITLE],
    ["sheet_identifier_value", "Valid Name", "", SHEET_IDENTIFIER_TITLE],
    [
      "sheet_identifier_value",
      "Invalid+value",
      "Only letters, numbers, spaces, underscores, and hyphens allowed",
      SHEET_IDENTIFIER_TITLE,
    ],
  
    // Sheet ID validation (no spaces allowed)
    ["sheet_identifier_value", "", "Sheet ID is required", SHEET_IDENTIFIER_ID],
    ["sheet_identifier_value", "Valid_Name", "", SHEET_IDENTIFIER_ID],
    [
      "sheet_identifier_value",
      "Invalid Name",
      "Only letters, numbers, underscores, and hyphens allowed (no spaces)",
      SHEET_IDENTIFIER_ID,
    ],
  ].forEach(([name, value, errorMessage, identifierType]) => {
    it(`validates the field name=${name}, value=${JSON.stringify(
      value
    )}, identifierType=${identifierType} and expects error=${JSON.stringify(errorMessage)}`, async () => {
      const wrapper = renderForm();
      
      const radio = wrapper.find(`input[name="sheet_identifier_type"][value="${identifierType}"]`);
      radio.simulate("change", { target: { name: "sheet_identifier_type", value: identifierType } });
  
      const input = wrapper.find(`textarea[name="${name}"]`);
      input.simulate("change", { persist: () => {}, target: { name, value } });
      input.simulate("blur");
      await wait();
      wrapper.update();

      assert.deepEqual(
        findFormikErrorByName(wrapper, name).text(),
        errorMessage
      );
    });
  });

  it("changes label text based on selected identifier type", async () => {
    const wrapper = renderForm();

    const getLabelText = () => wrapper.find("label[htmlFor='sheet_identifier_value']").text();
    
    assert.equal(getLabelText(), "Sheet ID*");
    
    const sheetTitleRadio = wrapper.find(`input[name='sheet_identifier_type'][value='${SHEET_IDENTIFIER_TITLE}']`);
    sheetTitleRadio.simulate("click");
    await wait();
    wrapper.update();

    assert.equal(getLabelText(), "Sheet Title*");
    
    const sheetIdRadio = wrapper.find(`input[name='sheet_identifier_type'][value='${SHEET_IDENTIFIER_ID}']`);
    sheetIdRadio.simulate("click");
    await wait();
    wrapper.update();

    assert.equal(getLabelText(), "Sheet ID*");
  });
});
