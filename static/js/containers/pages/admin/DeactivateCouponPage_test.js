// @flow
import { assert } from "chai";
import * as sinon from "sinon";

import DeactivateCouponPage, {
  DeactivateCouponPage as InnerDeactivateCouponPage,
} from "./DeactivateCouponPage";

import IntegrationTestHelper from "../../../util/integration_test_helper";
import { Modal } from "reactstrap";
import wait from "waait";

describe("DeactivateCouponPage", () => {
  let helper, renderDeactivateCouponPage, setSubmittingStub;

  beforeEach(() => {
    helper = new IntegrationTestHelper();
    setSubmittingStub = helper.sandbox.stub();
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
    await inner.instance().setState({ isDeactivated: true });

    let successMessage = `Coupon(s) successfully deactivated.`;

    assert.equal(inner.find(".coupon-success-div").text(), successMessage);

    // Mock the skipped_codes response
    const skippedCodes = ["xyz", "pqr"];
    inner.instance().setState({ skippedCodes: skippedCodes });

    successMessage += `The following coupon(s) are either already deactivated or the code(s) are incorrect.${skippedCodes.join("")}`;

    assert.equal(inner.find(".coupon-success-div").text(), successMessage);
  });

  it("sets state.isDeactivated if submission is successful", async () => {
    const testCouponsData = {
      coupons: "abc\nbcd",
    };
    helper.handleRequestStub.returns({
      body: {
        skipped_codes: ["xyz", "pqr"],
      },
    });
    const { inner } = await renderDeactivateCouponPage();

    await inner.instance().onSubmit(testCouponsData, {
      setSubmitting: setSubmittingStub,
    });
    sinon.assert.calledWith(setSubmittingStub, false);
    assert.isTrue(inner.find(Modal).exists());

    inner.find(".btn-gradient-red-to-blue").simulate("click");
    await wait;
    sinon.assert.calledWith(helper.handleRequestStub, "/api/coupons/", "PUT", {
      body: testCouponsData,
      headers: {
        "X-CSRFTOKEN": null,
      },
      credentials: undefined,
    });

    await wait;
    assert.equal(inner.state().isDeactivated, true);
  });

  it("clearSuccess() changes state.isDeactivated", async () => {
    const { inner } = await renderDeactivateCouponPage();
    inner.instance().setState({ isDeactivated: true });
    assert.equal(inner.state().isDeactivated, true);
    inner.instance().clearSuccess();
    assert.equal(inner.state().isDeactivated, false);
  });
});
