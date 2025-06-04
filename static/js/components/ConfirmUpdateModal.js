// @flow
import React from "react";
import { Modal, ModalHeader, ModalBody } from "reactstrap";

type Props = {|
  isOpen: boolean,
  toggle: () => void,
  onConfirm: () => void,
  submitting: boolean,
|};

export default function ConfirmUpdateModal({
  isOpen,
  toggle,
  onConfirm,
  submitting,
  headerMessage,
  bodyText,
}: Props) {
  return (
    <Modal isOpen={isOpen} toggle={toggle}>
      <ModalHeader toggle={toggle}>{headerMessage}</ModalHeader>
      <ModalBody>
        <div>{bodyText}</div>
        <div className="float-container">
          <button className="btn btn-gradient-white-to-blue" onClick={toggle}>
            Cancel
          </button>
          <button
            className="btn btn-gradient-red-to-blue"
            onClick={onConfirm}
            disabled={submitting}
          >
            Continue
          </button>
        </div>
      </ModalBody>
    </Modal>
  );
}
