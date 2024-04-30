// @flow
import { assert } from "chai";
import sinon from "sinon";

import RegisterDetailsPage, {
  RegisterDetailsPage as InnerRegisterDetailsPage,
} from "./RegisterDetailsPage";
import IntegrationTestHelper from "../../../util/integration_test_helper";
import {
  STATE_REGISTER_EXTRA_DETAILS,
  STATE_USER_BLOCKED,
  STATE_ERROR,
  STATE_ERROR_TEMPORARY,
  FLOW_REGISTER,
  STATE_EXISTING_ACCOUNT,
} from "../../../lib/auth";
import { routes } from "../../../lib/urls";
import { makeRegisterAuthResponse } from "../../../factories/auth";

describe("RegisterDetailsPage", () => {
  const detailsData = {
    name: "Sally",
    password: "password1",
    legal_address: {
      address: "main st",
    },
  };
  const partialToken = "partialTokenTestValue";
  const body = {
    flow: FLOW_REGISTER,
    partial_token: partialToken,
    ...detailsData,
  };
  let helper, renderPage, setSubmittingStub, setErrorsStub;

  beforeEach(() => {
    helper = new IntegrationTestHelper();

    setSubmittingStub = helper.sandbox.stub();
    setErrorsStub = helper.sandbox.stub();

    renderPage = helper.configureHOCRenderer(
      RegisterDetailsPage,
      InnerRegisterDetailsPage,
      {},
      {
        location: {
          search: `?partial_token=${partialToken}`,
        },
      },
    );
  });

  afterEach(() => {
    helper.cleanup();
  });

  it("displays a form", async () => {
    const { inner } = await renderPage();

    assert.ok(inner.find("RegisterDetailsForm").exists());
  });

  it("handles onSubmit for an error response", async () => {
    const { inner } = await renderPage();
    const error = "error message";
    const fieldErrors = {
      name: error,
    };

    helper.handleRequestStub.returns({
      body: makeRegisterAuthResponse({
        state: STATE_ERROR,
        field_errors: fieldErrors,
      }),
    });

    const onSubmit = inner.find("RegisterDetailsForm").prop("onSubmit");

    await onSubmit(detailsData, {
      setSubmitting: setSubmittingStub,
      setErrors: setErrorsStub,
    });

    sinon.assert.calledWith(
      helper.handleRequestStub,
      "/api/register/details/",
      "POST",
      { body, headers: undefined, credentials: undefined },
    );

    assert.lengthOf(helper.browserHistory, 1);
    sinon.assert.calledWith(setErrorsStub, fieldErrors);
    sinon.assert.calledWith(setSubmittingStub, false);
  });

  //
  [
    [STATE_ERROR_TEMPORARY, [], routes.register.error, ""],
    [STATE_ERROR, [], routes.register.error, ""], // cover the case with an error but no  messages
    [
      STATE_REGISTER_EXTRA_DETAILS,
      [],
      routes.register.extra,
      "?partial_token=new_partial_token",
    ],
    [
      STATE_USER_BLOCKED,
      ["error_code"],
      routes.register.denied,
      "?error=error_code",
    ],
    [STATE_USER_BLOCKED, [], routes.register.denied, ""],
  ].forEach(([state, errors, pathname, search]) => {
    it(`redirects to ${pathname} when it receives auth state ${state}`, async () => {
      const { inner } = await renderPage();

      helper.handleRequestStub.returns({
        body: makeRegisterAuthResponse({
          state,
          errors,
          partial_token: "new_partial_token",
        }),
      });

      const onSubmit = inner.find("RegisterDetailsForm").prop("onSubmit");

      await onSubmit(detailsData, {
        setSubmitting: setSubmittingStub,
        setErrors: setErrorsStub,
      });

      sinon.assert.calledWith(
        helper.handleRequestStub,
        "/api/register/details/",
        "POST",
        { body, headers: undefined, credentials: undefined },
      );

      assert.lengthOf(helper.browserHistory, 2);
      assert.include(helper.browserHistory.location, {
        pathname,
        search,
      });
      if (state === STATE_ERROR) {
        sinon.assert.calledWith(setErrorsStub, {});
      } else {
        sinon.assert.notCalled(setErrorsStub);
      }
      sinon.assert.calledWith(setSubmittingStub, false);
    });
  });

  it("displays a message with a login link for existing account", async () => {
    helper.handleRequestStub.returns({});
    const { inner } = await renderPage({
      entities: {
        auth: {
          state: STATE_EXISTING_ACCOUNT,
          partial_token: partialToken,
          extra_data: {},
        },
      },
    });
    const confirmationMessage = inner.find(".confirmation-message");
    assert.isNotNull(confirmationMessage);
    assert.equal(
      confirmationMessage.text().replace("<Link />", ""),
      "You already have an xPRO account. Please .",
    );
  });
});
