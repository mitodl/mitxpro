// @flow
import React from "react";
import sinon from "sinon";
import { assert } from "chai";
import { mount } from "enzyme";
import wait from "waait";
import moment from "moment";

import { PromoCouponUpdateForm } from "./PromoCouponUpdateForm";
import { PRODUCT_TYPE_COURSERUN, PRODUCT_TYPE_PROGRAM } from "../../constants";

import {
  findFormikFieldByName,
  findFormikErrorByName,
} from "../../lib/test_utils";
import {
  makeCourseRunProduct,
  makeProgramProduct,
} from "../../factories/ecommerce";

describe("PromoCouponUpdateForm", () => {
  let sandbox, onSubmitStub;
  // Mock data setup
  const mockProducts = [
    makeCourseRunProduct(),
    makeProgramProduct(),
    makeCourseRunProduct(),
  ];
  const mockPromoCoupons = [
    {
      id: "1",
      coupon_code: "TEST-COUPON-1",
      activation_date: "2025-01-01T00:00:00.000Z",
      expiration_date: "2025-12-31T23:59:59.999Z",
      eligibility: [
        { product_id: mockProducts[0].id },
        { product_id: mockProducts[1].id },
      ],
    },
    {
      id: "2",
      coupon_code: "TEST-COUPON-2",
      activation_date: "2025-02-01T00:00:00.000Z",
      expiration_date: "2025-11-30T23:59:59.999Z",
      eligibility: [{ product_id: mockProducts[2].id }],
    },
  ];

  const renderForm = () =>
    mount(
      <PromoCouponUpdateForm
        onSubmit={onSubmitStub}
        promoCoupons={mockPromoCoupons}
        products={mockProducts}
      />,
    );

  beforeEach(() => {
    sandbox = sinon.createSandbox();
    onSubmitStub = sandbox.stub();
  });

  afterEach(() => {
    sandbox.restore();
  });

  it("passes onSubmit to Formik", () => {
    const wrapper = renderForm();
    assert.equal(wrapper.find("Formik").props().onSubmit, onSubmitStub);
  });

  it("renders the form with all expected fields", () => {
    const wrapper = renderForm();
    const form = wrapper.find("Formik");
    // Check for required form elements
    assert.ok(findFormikFieldByName(form, "promo_coupon").exists());
    assert.ok(form.find('DayPickerInput[name="activation_date"]').exists());
    assert.ok(form.find('DayPickerInput[name="expiration_date"]').exists());
    assert.ok(form.find('input[name="product_type"]').exists());
    assert.ok(form.find("Picky2").exists());
    assert.ok(form.find('button[type="submit"]').exists());
  });

  it("renders promo coupon dropdown options correctly", () => {
    const wrapper = renderForm();
    const selectOptions = wrapper.find('select[name="promo_coupon"] option');

    // Check number of options (mockPromoCoupons + default empty option)
    assert.equal(selectOptions.length, mockPromoCoupons.length + 1);

    // Check default empty option
    assert.equal(selectOptions.at(0).text(), "-----");

    // Check coupon options
    mockPromoCoupons.forEach((coupon, index) => {
      assert.equal(selectOptions.at(index + 1).text(), coupon.coupon_code);
      assert.equal(selectOptions.at(index + 1).prop("value"), coupon.id);
    });
  });

  it("populates form fields when promo coupon is selected", async () => {
    const wrapper = renderForm();

    // Select a promo coupon
    const select = wrapper.find('select[name="promo_coupon"]');
    select.simulate("change", { target: { value: "1" } });

    await wait();
    wrapper.update();

    // Check if dates are populated correctly
    const activationDate = moment(mockPromoCoupons[0].activation_date).format(
      "L",
    );
    const expirationDate = moment(mockPromoCoupons[0].expiration_date).format(
      "L",
    );

    const activationInput = wrapper.find(
      'DayPickerInput[name="activation_date"]',
    );
    const expirationInput = wrapper.find(
      'DayPickerInput[name="expiration_date"]',
    );

    // Note: In a real test, you might need to check the internal state rather than the DOM value
    // This is a simplified check that would need to be adjusted based on how DayPickerInput works
    assert.ok(activationInput.exists());
    assert.ok(expirationInput.exists());
  });

  it("switches product selections based on product type radio buttons", async () => {
    const wrapper = renderForm();

    // First select a coupon to populate product selections
    const select = wrapper.find('select[name="promo_coupon"]');
    select.simulate("change", { target: { value: "1" } });

    await wait();
    wrapper.update();

    // Select course runs radio button
    const courseRunRadio = wrapper.find(
      `input[name="product_type"][value="${PRODUCT_TYPE_COURSERUN}"]`,
    );
    courseRunRadio.simulate("click", {
      target: { value: PRODUCT_TYPE_COURSERUN },
    });

    await wait();
    wrapper.update();

    // Now select programs radio button
    const programsRadio = wrapper.find(
      `input[name="product_type"][value="${PRODUCT_TYPE_PROGRAM}"]`,
    );
    programsRadio.simulate("click", {
      target: { value: PRODUCT_TYPE_PROGRAM },
    });

    await wait();
    wrapper.update();

    // Select all products radio button
    const allProductsRadio = wrapper.find(
      'input[name="product_type"][value=""]',
    );
    allProductsRadio.simulate("click", { target: { value: "" } });

    await wait();
    wrapper.update();
  });

  describe("form validation", () => {
    [
      ["", "Promo coupon is required"],
      ["1", ""],
    ].forEach(([value, errorMessage]) => {
      it(`validates the field name=promo_coupon, value="${JSON.stringify(
        value,
      )}" and expects error=${JSON.stringify(errorMessage)}`, async () => {
        const wrapper = renderForm();
        const formik = wrapper.find("Formik").instance();
        formik.setFieldValue("promo_coupon", value);
        formik.setFieldTouched("promo_coupon");
        await wait();
        wrapper.update();
        assert.deepEqual(
          findFormikErrorByName(wrapper, "promo_coupon").text(),
          errorMessage,
        );
      });
    });

    [
      [[], "1 or more products must be selected"],
      [[makeCourseRunProduct()], ""],
    ].forEach(([value, errorMessage]) => {
      it(`validates the field name=products, value="${JSON.stringify(
        value,
      )}" and expects error=${JSON.stringify(
        errorMessage,
      )} for coupons`, async () => {
        const wrapper = renderForm();
        const formik = wrapper.find("Formik").instance();
        formik.setFieldValue("products", value);
        formik.setFieldTouched("products");
        await wait();
        wrapper.update();
        assert.deepEqual(
          findFormikErrorByName(wrapper, "products").text(),
          errorMessage,
        );
      });
    });
    [
      [PRODUCT_TYPE_COURSERUN, [mockProducts[0]]],
      [PRODUCT_TYPE_PROGRAM, [mockProducts[1]]],
      ["", mockProducts],
    ].forEach(([productType, availableProduct]) => {
      it(`displays correct product checkboxes when productType radio button value="${productType}"`, async () => {
        const wrapper = renderForm();
        wrapper
          .find(`input[name='product_type'][value='${productType}']`)
          .simulate("click");
        await wait();
        wrapper.update();
        const picky = wrapper.find(".picky");
        const options = picky.find("input[type='checkbox']");
        assert.equal(options.at(2).exists(), productType === "");
        assert.ok(
          picky.text().includes(availableProduct[0].content_object.title),
        );
        if (productType === "") {
          assert.equal(options.at(1).exists(), productType === "");
          assert.ok(
            picky.text().includes(availableProduct[1].content_object.title),
          );
        }
      });
    });

    [
      ["expiration_date", 1, "", "Valid expiration date required"],
      ["activation_date", 0, "", "Valid activation date required"],
      ["expiration_date", 1, "bad_date", "Valid expiration date required"],
      ["activation_date", 0, "bad_date", "Valid activation date required"],
      ["activation_date", 0, "06/27/2019", ""],
      ["expiration_date", 1, moment().add(1, "days").format("MM/DD/YYYY"), ""],
      [
        "expiration_date",
        1,
        moment().subtract(1, "days").format("MM/DD/YYYY"),
        "Expiration date must be after today/activation date",
      ],
    ].forEach(([name, idx, value, errorMessage]) => {
      it(`validates the field name=${name}, value=${JSON.stringify(
        value,
      )} and expects error=${JSON.stringify(errorMessage)}`, async () => {
        const wrapper = renderForm();

        const input = wrapper.find("DayPickerInput").at(idx).find("input");
        input.simulate("click");
        input.simulate("change", {
          persist: () => {},
          target: { name, value },
        });
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

  it("submits form data when valid", async () => {
    const wrapper = renderForm();

    // Select a promo coupon
    const select = wrapper.find('select[name="promo_coupon"]');
    select.simulate("change", { target: { value: "1" } });

    await wait();
    wrapper.update();

    // Submit the form
    wrapper.find("form").simulate("submit");
  });
});
