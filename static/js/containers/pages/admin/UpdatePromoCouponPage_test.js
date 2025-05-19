// @flow
import { assert } from "chai";
import * as sinon from "sinon";

import UpdatePromoCouponPage, {
  UpdatePromoCouponPage as InnerUpdatePromoCouponPage,
} from "./UpdatePromoCouponPage";

import IntegrationTestHelper from "../../../util/integration_test_helper";
import { PromoCouponUpdateForm } from "../../../components/forms/PromoCouponUpdateForm";
import ConfirmUpdateModal from "../../../components/ConfirmUpdateModal";
import wait from "waait";
import {
  makeCourseRunProduct,
  makeProgramProduct,
} from "../../../factories/ecommerce";

describe("UpdatePromoCouponPage", () => {
  let helper, renderUpdatePromoCouponPage, setSubmittingStub;

  beforeEach(() => {
    helper = new IntegrationTestHelper();
    setSubmittingStub = helper.sandbox.stub();
    renderUpdatePromoCouponPage = helper.configureHOCRenderer(
      UpdatePromoCouponPage,
      InnerUpdatePromoCouponPage,
      {
        entities: {
          products: [
            {
              ...makeCourseRunProduct(),
              is_private: false,
            },
            {
              ...makeProgramProduct(),
              is_private: false,
            },
            {
              ...makeCourseRunProduct(),
              is_private: true,
            },
          ],
          promoCoupons: [
            { id: "coupon1", name: "Promo 1" },
            { id: "coupon2", name: "Promo 2" },
          ],
        },
      },
    );
  });

  afterEach(() => {
    helper.cleanup();
  });

  it("displays a promo coupon update form on the page", async () => {
    const { inner } = await renderUpdatePromoCouponPage();
    assert.isTrue(inner.find(PromoCouponUpdateForm).exists());
  });

  it("renders the ConfirmUpdateModal component", async () => {
    const { inner } = await renderUpdatePromoCouponPage();
    const modal = inner.find(ConfirmUpdateModal);
    assert.isTrue(modal.exists());
    assert.equal(modal.props().headerMessage, "Update Promo Coupon");
    assert.equal(
      modal.props().bodyText,
      "Update this promo coupon? This will overwrite existing product eligibility settings.",
    );
  });

  it("filters private products from being passed to the form", async () => {
    const { inner } = await renderUpdatePromoCouponPage();
    const form = inner.find(PromoCouponUpdateForm);
    assert.equal(form.props().products.length, 2);
    assert.isFalse(
      form.props().products.some((product) => product.is_private === true),
    );
  });

  it("displays a success message on the page after update", async () => {
    const { inner } = await renderUpdatePromoCouponPage();

    // Set state to simulate successful update with response message
    await inner.instance().setState({
      isUpdated: true,
      responseMsg: "Promo coupon successfully updated.",
    });

    const successMessage = inner.find(".form-success");
    assert.isTrue(successMessage.exists());
    assert.equal(
      successMessage.find(".message-text").text(),
      "Promo coupon successfully updated.",
    );
  });

  it("displays an error message when update fails", async () => {
    const { inner } = await renderUpdatePromoCouponPage();

    // Set state to simulate failed update with error message
    await inner.instance().setState({
      isUpdated: true,
      responseMsg: "",
      errorMsg: "Failed to update promo coupon.",
    });

    const errorMessage = inner.find(".form-warning");
    assert.isTrue(errorMessage.exists());
    assert.equal(
      errorMessage.find(".message-text").text(),
      "Failed to update promo coupon.",
    );
  });

  it("toggles the confirmation modal when onSubmit is called", async () => {
    const testCouponData = {
      id: "coupon1",
      products: [{ id: "1" }, { id: "2" }],
    };

    const { inner } = await renderUpdatePromoCouponPage();

    // Initially modal should be closed
    assert.isFalse(inner.state().openConfirmModal);

    // Call onSubmit which should open the modal
    await inner.instance().onSubmit(testCouponData, {
      setSubmitting: setSubmittingStub,
    });

    sinon.assert.calledWith(setSubmittingStub, false);
    assert.isTrue(inner.state().openConfirmModal);
    assert.deepEqual(inner.state().couponData, testCouponData);
  });

  it("toggles the confirmation modal with toggleOpenConfirmModal", async () => {
    const { inner } = await renderUpdatePromoCouponPage();

    // Initial state
    assert.isFalse(inner.state().openConfirmModal);

    // Toggle modal open
    await inner.instance().toggleOpenConfirmModal();
    assert.isTrue(inner.state().openConfirmModal);

    // Toggle modal closed
    await inner.instance().toggleOpenConfirmModal();
    assert.isFalse(inner.state().openConfirmModal);
  });

  it("closes the modal when modal confirmation button is clicked", async () => {
    const updatePromoCouponStub = helper.handleRequestStub.returns({
      body: {
        message: "Promo coupon successfully updated.",
      },
    });

    const { inner } = await renderUpdatePromoCouponPage({
      updatePromoCoupon: updatePromoCouponStub,
    });

    // Set modal to open and coupon data
    await inner.instance().setState({
      openConfirmModal: true,
      couponData: {
        id: "coupon1",
        products: [{ id: "1" }],
      },
    });

    // Verify modal is open
    const modal = inner.find(ConfirmUpdateModal);
    assert.isTrue(modal.exists());
    assert.isTrue(modal.props().isOpen);

    // Simulate confirmation click
    await modal.props().onConfirm();
    await wait;

    // Modal should be closed after confirmation
    assert.isFalse(inner.state().openConfirmModal);
    assert.isTrue(inner.state().isUpdated);
  });

  it("updates promo coupon when onModalSubmit is called", async () => {
    const testCouponData = {
      id: "coupon1",
      products: [{ id: "1" }, { id: "2" }],
    };

    helper.handleRequestStub.returns({
      body: {
        message: "Promo coupon successfully updated.",
      },
    });

    const { inner } = await renderUpdatePromoCouponPage();

    // Set up the state with coupon data
    await inner.instance().setState({
      couponData: testCouponData,
      openConfirmModal: true,
    });

    // Call onModalSubmit
    await inner.instance().onModalSubmit();

    // After update, the state should be updated appropriately
    assert.equal(inner.state().isUpdated, true);
    assert.equal(inner.state().openConfirmModal, false);
    assert.equal(inner.state().submitting, false);
    assert.equal(
      inner.state().responseMsg,
      "Promo coupon successfully updated.",
    );
  });

  it("clearSuccess() resets the state", async () => {
    const { inner } = await renderUpdatePromoCouponPage();

    // Set a state to clear
    inner.instance().setState({
      isUpdated: true,
      openConfirmModal: true,
      couponData: { id: "test" },
      errorMsg: "Error",
      responseMsg: "Success",
    });

    // Verify initial state
    assert.equal(inner.state().isUpdated, true);
    assert.equal(inner.state().openConfirmModal, true);
    assert.deepEqual(inner.state().couponData, { id: "test" });
    assert.equal(inner.state().errorMsg, "Error");
    assert.equal(inner.state().responseMsg, "Success");

    // Call clearSuccess
    await inner.instance().clearSuccess();

    // Verify state has been reset
    assert.equal(inner.state().isUpdated, false);
    assert.equal(inner.state().openConfirmModal, false);
    assert.deepEqual(inner.state().couponData, {});
    assert.equal(inner.state().errorMsg, "");
    assert.equal(inner.state().responseMsg, "");
  });

  it("renders a link back to ecommerce admin", async () => {
    const { inner } = await renderUpdatePromoCouponPage();
    const backLink = inner.find("Link");
    assert.isTrue(backLink.exists());
    assert.equal(backLink.props().to, "/ecommerce/admin/");
  });
});
