// @flow
import React from "react";
import sinon from "sinon";
import { assert } from "chai";
import { mount } from "enzyme";
import { Modal, ModalHeader, ModalBody } from "reactstrap";

import ConfirmUpdateModal from "./ConfirmUpdateModal";

describe("ConfirmUpdateModal", () => {
  let sandbox, onConfirmStub, toggleStub;

  const defaultProps = {
    isOpen: true,
    toggle: () => {},
    onConfirm: () => {},
    submitting: false,
    headerMessage: "Confirm Update",
    bodyText: "Are you sure you want to continue?",
  };

  const renderModal = (props = {}) =>
    mount(<ConfirmUpdateModal {...defaultProps} {...props} />);

  beforeEach(() => {
    sandbox = sinon.createSandbox();
    onConfirmStub = sandbox.stub();
    toggleStub = sandbox.stub();
  });

  afterEach(() => {
    sandbox.restore();
  });

  it("renders the Modal component with correct props", () => {
    const wrapper = renderModal({
      isOpen: true,
      toggle: toggleStub,
    });

    const modal = wrapper.find(Modal);
    assert.ok(modal.exists(), "Modal component should be rendered");
    assert.isTrue(modal.prop("isOpen"), "Modal should be open");
    assert.equal(
      modal.prop("toggle"),
      toggleStub,
      "Toggle prop should be passed to Modal",
    );
  });

  it("renders the header with the provided headerMessage", () => {
    const headerMessage = "Custom Header Message";
    const wrapper = renderModal({
      headerMessage: headerMessage,
    });

    const modalHeader = wrapper.find(ModalHeader);
    assert.ok(modalHeader.exists(), "ModalHeader component should be rendered");
    assert.include(
      modalHeader.text(),
      headerMessage,
      "Header should contain the provided message",
    );
    assert.equal(
      modalHeader.prop("toggle"),
      defaultProps.toggle,
      "Toggle prop should be passed to ModalHeader",
    );
  });

  it("renders the body with the provided bodyText", () => {
    const bodyText = "Custom body text for testing";
    const wrapper = renderModal({
      bodyText: bodyText,
    });

    const modalBody = wrapper.find(ModalBody);
    assert.ok(modalBody.exists(), "ModalBody component should be rendered");
    assert.include(
      modalBody.text(),
      bodyText,
      "Body should contain the provided text",
    );
  });

  it("renders Cancel and Continue buttons", () => {
    const wrapper = renderModal();

    const buttons = wrapper.find("button");
    assert.equal(
      buttons.length,
      3,
      "Should render three buttons including the default close button",
    );

    const cancelButton = buttons.at(1);
    assert.include(
      cancelButton.text(),
      "Cancel",
      "First button should be Cancel",
    );

    const continueButton = buttons.at(2);
    assert.include(
      continueButton.text(),
      "Continue",
      "Second button should be Continue",
    );
  });

  it("disables the Continue button when submitting is true", () => {
    const wrapper = renderModal({
      submitting: true,
    });

    const continueButton = wrapper.find("button").at(2);
    assert.isTrue(
      continueButton.prop("disabled"),
      "Continue button should be disabled when submitting",
    );
  });

  it("enables the Continue button when submitting is false", () => {
    const wrapper = renderModal({
      submitting: false,
    });

    const continueButton = wrapper.find("button").at(2);
    assert.isFalse(
      continueButton.prop("disabled"),
      "Continue button should be enabled when not submitting",
    );
  });

  it("calls toggle when Cancel button is clicked", () => {
    const wrapper = renderModal({
      toggle: toggleStub,
    });

    const cancelButton = wrapper.find("button").at(0);
    cancelButton.simulate("click");

    assert.isTrue(
      toggleStub.calledOnce,
      "Toggle should be called once when Cancel button is clicked",
    );
  });

  it("calls onConfirm when Continue button is clicked", () => {
    const wrapper = renderModal({
      onConfirm: onConfirmStub,
    });

    const continueButton = wrapper.find("button").at(2);
    continueButton.simulate("click");

    assert.isTrue(
      onConfirmStub.calledOnce,
      "onConfirm should be called once when Continue button is clicked",
    );
  });

  it("doesn't call onConfirm when Continue button is clicked but disabled", () => {
    const wrapper = renderModal({
      onConfirm: onConfirmStub,
      submitting: true,
    });

    const continueButton = wrapper.find("button").at(1);
    continueButton.simulate("click");

    assert.isFalse(
      onConfirmStub.called,
      "onConfirm should not be called when Continue button is disabled",
    );
  });
});
