// @flow
import { assert } from "chai";
import * as sinon from "sinon";

import ProcessCouponAssignmentSheetPage, {
  ProcessCouponAssignmentSheetPage as InnerProcessCouponAssignmentSheetPage,
} from "./ProcessCouponAssignmentSheetPage";

import IntegrationTestHelper from "../../../util/integration_test_helper";
import wait from "waait";

describe("ProcessCouponAssignmentSheetPage", () => {
  let helper, renderProcessCouponAssignmentSheetPage, setSubmittingStub;

  beforeEach(() => {
    helper = new IntegrationTestHelper();
    setSubmittingStub = helper.sandbox.stub();
    renderProcessCouponAssignmentSheetPage = helper.configureHOCRenderer(
      ProcessCouponAssignmentSheetPage,
      InnerProcessCouponAssignmentSheetPage,
    );
  });

  afterEach(() => {
    helper.cleanup();
  });

  it("displays a coupon sheet process form on the page", async () => {
    const { inner } = await renderProcessCouponAssignmentSheetPage();
    assert.isTrue(inner.find("CouponSheetProcessForm").exists());
  });

  it("displays a success message on the page", async () => {
    const { inner } = await renderProcessCouponAssignmentSheetPage();

    // Success Case
    const successMsg = `Successfully processed coupon assignment sheet.`;
    await inner.instance().setState({
      isProcessed: true,
      responseMsg: successMsg,
      numCreated: 4,
      numRemoved: 2,
    });
    assert.equal(
      inner.find(".coupon-result-div").text(),
      `${successMsg}Number of Coupon Assignment created: 4Number of Coupon Assignment removed: 2`,
    );

    // Error Case
    const errorMsg = "Error processing coupon assignment sheet.";
    inner
      .instance()
      .setState({ isProcessed: true, responseMsg: "", errorMsg: errorMsg });
    assert.equal(inner.find(".coupon-result-div").text(), errorMsg);
  });

  it("sets state.isProcessed if submission is successful", async () => {
    const testPayloadData = {
      sheet_identifier_type: "id",
      sheet_identifier_value: "123",
    };
    helper.handleRequestStub.returns({
      body: {
        message:
          "Successfully processed coupon assignment sheet  ('abc', id: 123).",
      },
    });
    const { inner } = await renderProcessCouponAssignmentSheetPage();

    await inner.instance().onSubmit(testPayloadData, {
      setSubmitting: setSubmittingStub,
    });
    sinon.assert.calledWith(setSubmittingStub, false);

    await wait;
    sinon.assert.calledWith(
      helper.handleRequestStub,
      "/api/sheets/process_coupon_sheet_assignment/",
      "POST",
      {
        body: testPayloadData,
        headers: {
          "X-CSRFTOKEN": null,
        },
        credentials: undefined,
      },
    );
  });

  it("clearSuccess() changes state.isProcessed", async () => {
    const { inner } = await renderProcessCouponAssignmentSheetPage();
    inner.instance().setState({ isProcessed: true });
    assert.equal(inner.state().isProcessed, true);
    inner.instance().clearSuccess();
    assert.equal(inner.state().isProcessed, false);
  });
});
