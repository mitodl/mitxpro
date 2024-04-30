// @flow
import React from "react";
import { curry } from "ramda";

const BaseTextInput = curry((inputType, { field, form, ...props }) => {
  const { touched, errors } = form;
  const errored = touched[field.name] && errors[field.name];
  const addedClasses = errored ? "errored" : "";
  return (
    <input
      type={inputType}
      {...field}
      {...props}
      className={`${props.className || ""} ${addedClasses}`}
    />
  );
});

export const TextInput = BaseTextInput("text");
export const EmailInput = BaseTextInput("email");
export const PasswordInput = BaseTextInput("password");
