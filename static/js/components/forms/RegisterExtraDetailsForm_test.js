// @flow
import React from "react";
import sinon from "sinon";
import { assert } from "chai";
import { mount } from "enzyme";
import wait from "waait";

import RegisterExtraDetailsForm from "./RegisterExtraDetailsForm";

import {
  findFormikFieldByName,
  findFormikErrorByName,
} from "../../lib/test_utils";

describe("RegisterExtraDetailsForm", () => {
  let sandbox, onSubmitStub;

  const renderForm = () =>
    mount(<RegisterExtraDetailsForm onSubmit={onSubmitStub} />);

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
    assert.ok(findFormikFieldByName(form, "profile.birth_year").exists());
    assert.ok(findFormikFieldByName(form, "profile.company_size").exists());
    assert.ok(form.find("button[type='submit']").exists());
  });

  //
  [
    ["profile.company", "", "Company is a required field"],
    ["profile.company", "  ", "Company is a required field"],
    ["profile.company", "MIT", ""],
    ["profile.job_title", "", "Job Title is a required field"],
    ["profile.job_title", "  ", "Job Title is a required field"],
    ["profile.job_title", "QA Tester", ""],
  ].forEach(([name, value, errorMessage]) => {
    it(`validates the field name=${name}, value=${JSON.stringify(
      value,
    )} and expects error=${JSON.stringify(errorMessage)}`, async () => {
      const wrapper = renderForm();

      const input = wrapper.find(`input[name="${name}"]`);
      input.simulate("change", { persist: () => {}, target: { name, value } });
      input.simulate("blur");
      await wait();
      wrapper.update();
      assert.deepEqual(
        findFormikErrorByName(wrapper, name).text(),
        errorMessage,
      );
    });
  });

  //
  [
    ["profile.gender", "", "Gender is a required field"],
    ["profile.gender", "f", ""],
    ["profile.birth_year", "", "Birth Year is a required field"],
    ["profile.birth_year", "2000", ""],
  ].forEach(([name, value, errorMessage]) => {
    it(`validates the field name=${name}, value=${JSON.stringify(
      value,
    )} and expects error=${JSON.stringify(errorMessage)}`, async () => {
      const wrapper = renderForm();

      const input = wrapper.find(`select[name="${name}"]`);
      input.simulate("change", { persist: () => {}, target: { name, value } });
      input.simulate("blur");
      await wait();
      wrapper.update();
      assert.deepEqual(
        findFormikErrorByName(wrapper, name).text(),
        errorMessage,
      );
    });
  });
});
