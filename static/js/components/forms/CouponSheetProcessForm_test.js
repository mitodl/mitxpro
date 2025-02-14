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
    ["sheet_identifier_value", "", "Sheet ID or Title is required"],
    ["sheet_identifier_value", "Valid_name", ""],
    [
      "sheet_identifier_value",
      "Invalid+value",
      "Only letters, numbers, spaces, underscores, and hyphens allowed",
    ],
  ].forEach(([name, value, errorMessage]) => {
    it(`validates the field name=${name}, value=${JSON.stringify(
      value
    )} and expects error=${JSON.stringify(errorMessage)}`, async () => {
      const wrapper = renderForm();
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
