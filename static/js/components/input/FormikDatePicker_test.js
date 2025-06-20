// @flow
import React from "react";
import { assert } from "chai";
import sinon from "sinon";
import { mount } from "enzyme";
import { format } from "date-fns";
import FormikDatePicker from "./FormikDatePicker";
import * as utils from "../../lib/util";
import IntegrationTestHelper from "../../util/integration_test_helper";

describe("FormikDatePicker", () => {
  let helper, props, clock;

  before(() => {
    // Patch the FormError module before the component imports it
    const modulePath = require.resolve("../forms/elements/FormError");
    const fakeFormError = () => <div className="form-error">FormError</div>;
    require.cache[modulePath] = {
      id: modulePath,
      filename: modulePath,
      loaded: true,
      exports: fakeFormError,
    };
  });

  beforeEach(() => {
    helper = new IntegrationTestHelper();
    props = {
      name: "test_date",
      label: "Test Date",
      values: {},
      setFieldValue: helper.sandbox.stub(),
      setFieldTouched: helper.sandbox.stub(),
    };
    helper.sandbox.stub(utils, "zeroHour");
    helper.sandbox.stub(utils, "finalHour");
    clock = sinon.useFakeTimers(new Date("2025-06-15").getTime());
  });

  afterEach(() => {
    helper.cleanup();
    clock.restore();
  });

  it("renders input and label", () => {
    const wrapper = mount(<FormikDatePicker {...props} />);
    assert.include(wrapper.find("label").text(), "Test Date");
    assert.isTrue(wrapper.find("input[type='text']").exists());
  });

  it("displays formatted date if value is set", () => {
    const date = new Date("2025-06-12");
    props.values = { test_date: date };
    const wrapper = mount(<FormikDatePicker {...props} />);
    assert.equal(
      wrapper.find("input").prop("value"),
      format(date, "MM/dd/yyyy"),
    );
  });

  it("toggles calendar when input is clicked", () => {
    const wrapper = mount(<FormikDatePicker {...props} />);
    const input = wrapper.find("input");

    assert.isFalse(wrapper.find(".date-picker-container").exists());
    input.simulate("click");
    assert.isTrue(wrapper.find(".date-picker-container").exists());
    input.simulate("click");
    assert.isFalse(wrapper.find(".date-picker-container").exists());
  });

  it("selects a date and updates form state", () => {
    const wrapper = mount(
      <FormikDatePicker {...props} name="activation_date" />,
    );
    wrapper.find("input").simulate("click");

    const today = wrapper.find(".rdp-day_button").first();
    today.simulate("click");

    assert.isTrue(utils.zeroHour.calledOnce);
    assert.isTrue(props.setFieldValue.calledOnce);
    assert.isTrue(props.setFieldTouched.called);
    assert.isFalse(wrapper.find(".date-picker-container").exists());
  });

  it("closes calendar on outside click", () => {
    const wrapper = mount(
      <div>
        <FormikDatePicker {...props} />
        <div id="outside">Outside</div>
      </div>,
    );

    wrapper.find("input").simulate("click");
    assert.isTrue(wrapper.find(".date-picker-container").exists());

    document.dispatchEvent(new MouseEvent("mousedown", { bubbles: true }));
    wrapper.update();

    assert.isFalse(wrapper.find(".date-picker-container").exists());
  });
});
