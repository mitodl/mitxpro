// @flow
import casual from "casual-browserify";

import { FLOW_LOGIN, FLOW_REGISTER } from "../lib/auth";

import type { AuthResponse, AuthFlow, AuthStates } from "../flow/authTypes";

export const makeAuthResponse = (
  values: $Shape<AuthResponse> & {
    state: AuthStates,
    flow: AuthFlow,
  },
): AuthResponse => ({
  errors: [],
  field_errors: {},
  partial_token: casual.uuid,
  redirect_url: undefined,
  extra_data: {},
  ...values,
});

export const makeLoginAuthResponse = (
  values: $Shape<AuthResponse> & {
    state: AuthStates,
  },
): AuthResponse =>
  makeAuthResponse({
    flow: FLOW_LOGIN,
    ...values,
  });

export const makeRegisterAuthResponse = (
  values: $Shape<AuthResponse> & {
    state: AuthStates,
  },
): AuthResponse =>
  makeAuthResponse({
    flow: FLOW_REGISTER,
    ...values,
  });
