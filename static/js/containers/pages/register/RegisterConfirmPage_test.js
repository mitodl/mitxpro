// @flow
import { assert } from "chai";
import sinon from "sinon";

import IntegrationTestHelper from "../../../util/integration_test_helper";
import RegisterConfirmPage, {
  RegisterConfirmPage as InnerRegisterConfirmPage,
} from "./RegisterConfirmPage";
import {
  FLOW_REGISTER,
  STATE_REGISTER_CONFIRM_REQUIRED,
  STATE_REGISTER_DETAILS,
  STATE_INVALID_LINK,
  STATE_EXISTING_ACCOUNT,
  STATE_INVALID_EMAIL,
} from "../../../lib/auth";
import { routes } from "../../../lib/urls";

describe("RegisterConfirmPage", () => {
  let helper, renderPage;

  beforeEach(() => {
    helper = new IntegrationTestHelper();
    renderPage = helper.configureHOCRenderer(
      RegisterConfirmPage,
      InnerRegisterConfirmPage,
      {},
      {
        location: {
          search: "",
        },
      },
    );
  });

  afterEach(() => {
    helper.cleanup();
  });

  it("shows a message when the confirmation page is displayed and redirects", async () => {
    helper.handleRequestStub.returns({});
    const token = "asdf";
    const { inner, store } = await renderPage({
      entities: {
        auth: {
          state: STATE_REGISTER_DETAILS,
          partial_token: token,
          extra_data: {
            name: "name",
          },
        },
      },
    });

    inner.instance().componentDidUpdate({}, {});
    assert.deepEqual(store.getState().ui.userNotifications, {
      "email-verified": {
        type: "text",
        props: {
          text: "Success! We've verified your email. Please finish your account creation below.",
        },
      },
    });
    assert.equal(
      helper.currentLocation.location.pathname,
      "/create-account/details/",
    );
    assert.equal(
      helper.currentLocation.location.search,
      `?partial_token=${token}`,
    );
  });

  it("Shows a register link with invalid/expired confirmation code", async () => {
    helper.handleRequestStub.returns({});
    const token = "asdf";
    const { inner, store } = await renderPage({
      entities: {
        auth: {
          state: STATE_INVALID_LINK,
          partial_token: token,
          extra_data: {},
        },
      },
    });
    const confirmationErrorText = inner.find(".confirmation-message");
    assert.isNotNull(confirmationErrorText);
    assert.equal(
      confirmationErrorText.text().replace("<Link />", ""),
      "This invitation is invalid or has expired. Please .",
    );
  });

  it("Shows a login link with existing account message", async () => {
    helper.handleRequestStub.returns({});
    const token = "asdf";
    const { inner, store } = await renderPage({
      entities: {
        auth: {
          state: STATE_EXISTING_ACCOUNT,
          partial_token: token,
          extra_data: {},
        },
      },
    });
    const confirmationErrorText = inner.find(".confirmation-message");
    assert.isNotNull(confirmationErrorText);
    assert.equal(
      confirmationErrorText.text().replace("<Link />", ""),
      "You already have an xPRO account. Please .",
    );
  });

  it("Shows a register link with invalid or no confirmation code", async () => {
    helper.handleRequestStub.returns({});
    const token = "asdf";
    const { inner, store } = await renderPage({
      entities: {
        auth: {
          state: STATE_INVALID_EMAIL,
          partial_token: token,
          extra_data: {},
        },
      },
    });
    const confirmationErrorText = inner.find(".confirmation-message");
    assert.equal(
      confirmationErrorText.text().replace("<Link />", ""),
      "No confirmation code was provided or it has expired. .",
    );
  });

  describe("when the link was opened in another browser", () => {
    const email = "someone@example.com";
    const nonce = "a-nonce";
    const confirmRequiredAuth = {
      state: STATE_REGISTER_CONFIRM_REQUIRED,
      partial_token: null,
      extra_data: { email, confirmation_nonce: nonce },
    };

    it("asks the user to confirm the email before continuing", async () => {
      helper.handleRequestStub.returns({});
      const { inner } = await renderPage({
        entities: { auth: confirmRequiredAuth },
      });

      assert.include(inner.find(".confirmation-message").text(), email);
      assert.equal(inner.find("button").text(), "Continue");
      const link = inner.find(".not-my-email Link");
      assert.equal(link.prop("to"), routes.register.begin);
      assert.equal(
        link.prop("children"),
        "Create an account with a different email",
      );
    });

    it("sends the confirmation only once when Continue is clicked repeatedly", async () => {
      helper.handleRequestStub.returns({});
      const { inner } = await renderPage(
        { entities: { auth: confirmRequiredAuth } },
        { location: { search: "?verification_code=code&partial_token=token" } },
      );
      helper.handleRequestStub.resetHistory();

      const first = inner.instance().onContinue();
      const second = inner.instance().onContinue();
      inner.update();
      assert.isTrue(inner.find("button").prop("disabled"));
      await Promise.all([first, second]);

      sinon.assert.calledOnce(helper.handleRequestStub);
      inner.update();
      assert.isFalse(inner.find("button").prop("disabled"));
    });

    it("confirms with the nonce when the user clicks Continue", async () => {
      const qsParams = { verification_code: "code", partial_token: "token" };
      helper.handleRequestStub.returns({});
      const { inner } = await renderPage(
        { entities: { auth: confirmRequiredAuth } },
        { location: { search: "?verification_code=code&partial_token=token" } },
      );
      helper.handleRequestStub.resetHistory();

      inner.find("button").simulate("click");

      sinon.assert.calledWith(
        helper.handleRequestStub,
        "/api/register/confirm/",
        "POST",
        {
          body: {
            flow: FLOW_REGISTER,
            ...qsParams,
            partial_pipeline_confirm: "1",
            partial_pipeline_confirm_nonce: nonce,
          },
          headers: undefined,
          credentials: undefined,
        },
      );
    });
  });
});
