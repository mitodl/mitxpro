// @flow
import React from "react";
import sinon from "sinon";
import moment from "moment";
import { assert } from "chai";
import { mount } from "enzyme";
import wait from "waait";

import { CouponDeactivateForm } from "./CouponDeactivateForm";

import {
  findFormikFieldByName,
  findFormikErrorByName,
} from "../../lib/test_utils";

describe("CouponDeactivateForm", () => {
  let sandbox, onSubmitStub;

  const renderForm = () =>
    mount(<CouponDeactivateForm onSubmit={onSubmitStub} />);

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
    assert.ok(findFormikFieldByName(form, "coupons").exists());
    assert.ok(form.find("button[type='submit']").exists());
  });

  [
    ["coupons", "", "At least one coupon name or code is required"],
    ["coupons", "Valid_name", ""],
    [
      "coupons",
      "Invalid name",
      "Only letters, numbers, and underscores allowed",
    ],
  ].forEach(([name, value, errorMessage]) => {
    it(`validates the field name=${name}, value=${JSON.stringify(
      value,
    )} and expects error=${JSON.stringify(errorMessage)}`, async () => {
      const wrapper = renderForm();

      const input = wrapper.find(`textarea[name="${name}"]`);
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
