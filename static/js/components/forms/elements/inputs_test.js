// @flow
import React from "react";
import { assert } from "chai";
import { shallow } from "enzyme";

import { TextInput, EmailInput, PasswordInput } from "./inputs";
import { isIf } from "../../../lib/test_utils";

describe("Form input", () => {
  describe("for text", () => {
    const fieldName = "myField";
    const defaultProps = {
      field: { name: fieldName },
      form: {
        touched: { [fieldName]: false },
        errors: { [fieldName]: null },
      },
    };

    it("has the right input type", () => {
      const textInput = shallow(<TextInput {...defaultProps} />);
      assert.equal(textInput.prop("type"), "text");
      const emailInput = shallow(<EmailInput {...defaultProps} />);
      assert.equal(emailInput.prop("type"), "email");
      const passwordInput = shallow(<PasswordInput {...defaultProps} />);
      assert.equal(passwordInput.prop("type"), "password");
    });
    [
      ["some-class", false, "some-class "],
      ["", true, " errored"],
      ["some-class", true, "some-class errored"],
    ].forEach(([className, isErrored, expClassName]) => {
      it(`has the right class names if class ${isIf(
        !!className,
      )} specified and ${isIf(isErrored)} in error state`, () => {
        const props = {
          ...defaultProps,
          form: {
            touched: {
              [fieldName]: isErrored,
            },
            errors: {
              [fieldName]: isErrored ? "ERROR" : null,
            },
          },
        };
        const textInput = shallow(
          <TextInput className={className} {...props} />,
        );
        assert.equal(textInput.prop("className"), expClassName);
      });
    });
  });
});
