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
    await inner.instance().setState({ deactivated: true });
    assert.equal(
      inner.find(".coupon-success-div").text(),
      `Coupon(s) successfully deactivated.`,
    );
  });

  it("sets state.couponId to new coupon id if submission is successful", async () => {
    const testCouponsData = {
      coupons: "abc\nbcd",
    };
    helper.handleRequestStub.returns({
      body: { status: "Deactivated coupon(s) sucessfully!" },
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

  it("clearSuccess() changes state.couponId", async () => {
    const { inner } = await renderDeactivateCouponPage();
    inner.instance().setState({ deactivated: true });
    assert.equal(inner.state().deactivated, true);
    inner.instance().clearSuccess();
    assert.equal(inner.state().deactivated, false);
  });
});
