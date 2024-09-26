// @flow
import { assert } from "chai";
import * as sinon from "sinon";

import DeactivateCouponPage, {
  DeactivateCouponPage as InnerDeactivateCouponPage,
} from "./DeactivateCouponPage";

import IntegrationTestHelper from "../../../util/integration_test_helper";

describe("DeactivateCouponPage", () => {
  let helper, renderDeactivateCouponPage, setSubmittingStub, setErrorsStub;

  beforeEach(() => {
    helper = new IntegrationTestHelper();
    setSubmittingStub = helper.sandbox.stub();
    setErrorsStub = helper.sandbox.stub();
    renderDeactivateCouponPage = helper.configureHOCRenderer(
      DeactivateCouponPage,
      InnerDeactivateCouponPage,
    );
  });

  afterEach(() => {
    helper.cleanup();
  });

  it("displays a coupon form on the page", async () => {
    const { inner } = await renderDeactivateCouponPage();
    assert.isTrue(inner.find("CouponDeactivateForm").exists());
  });

  it("displays a success message on the page", async () => {
    const { inner } = await renderDeactivateCouponPage();
    // Without skipped codes
    await inner.instance().setState({ deactivated: true });

    let successMessage = `Coupon(s) successfully deactivated.`;

    assert.equal(inner.find(".coupon-success-div").text(), successMessage);

    // Mock the skipped_codes response
    const skippedCodes = ["xyz", "pqr"];
    inner.instance().setState({ skippedCodes: skippedCodes });

    successMessage += `The following coupon(s) were skipped:${skippedCodes.join("")}The coupon(s) is/are either already deactivated or the code(s) is/are incorrect.`;

    assert.equal(inner.find(".coupon-success-div").text(), successMessage);
  });

  it("sets state.deactivated if submission is successful", async () => {
    const testCouponsData = {
      coupons: "abc\nbcd",
    };
    helper.handleRequestStub.returns({
      body: {
        status: "Deactivated coupon(s) successfully!",
        skipped_codes: ["xyz", "pqr"],
      },
    });
    const { inner } = await renderDeactivateCouponPage();

    await inner.instance().onSubmit(testCouponsData, {
      setSubmitting: setSubmittingStub,
      setErrors: setErrorsStub,
    });
    sinon.assert.calledWith(setSubmittingStub, false);
    sinon.assert.notCalled(setErrorsStub);
    sinon.assert.calledWith(helper.handleRequestStub, "/api/coupons/", "PUT", {
      body: testCouponsData,
      headers: {
        "X-CSRFTOKEN": null,
      },
      credentials: undefined,
    });
    assert.equal(inner.state().deactivated, true);
  });

  it("clearSuccess() changes state.deactivated", async () => {
    const { inner } = await renderDeactivateCouponPage();
    inner.instance().setState({ deactivated: true });
    assert.equal(inner.state().deactivated, true);
    inner.instance().clearSuccess();
    assert.equal(inner.state().deactivated, false);
  });
});
