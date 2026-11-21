// @flow
import sinon from "sinon";
import { assert } from "chai";
import { createMemoryHistory } from "history";

import {
  ALL_STATES,
  FLOW_LOGIN,
  FLOW_REGISTER,
  STATE_SESSION_EXPIRED,
  generateLoginRedirectUrl,
  handleAuthResponse,
} from "./auth";
import { routes } from "../lib/urls";
import {
  makeLoginAuthResponse,
  makeRegisterAuthResponse,
} from "../factories/auth";

describe("auth lib function", () => {
  it("generateLoginRedirectUrl should generate a url to redirect to after login", () => {
    window.location = "/protected/route?var=abc";
    const redirectUrl = generateLoginRedirectUrl();
    assert.equal(
      redirectUrl,
      `${routes.login.begin}?next=%2Fprotected%2Froute%3Fvar%3Dabc`,
    );
  });

  describe("handleAuthResponse", () => {
    let history, sandbox;

    beforeEach(() => {
      history = createMemoryHistory();
      sandbox = sinon.createSandbox();
    });

    afterEach(() => {
      sandbox.restore();
    });

    ALL_STATES.forEach((state) => {
      it(`calls a corresponding handlers function for state=${state}`, () => {
        // the flow type doesn't pertain here so register response is fine
        const response = makeRegisterAuthResponse({ state });
        const handler = sinon.stub();
        const handlers = {
          [state]: handler,
        };

        handleAuthResponse(history, response, handlers);

        sinon.assert.calledWith(handler, response);
      });
    });

    [
      [FLOW_LOGIN, makeLoginAuthResponse, routes.login.begin],
      [FLOW_REGISTER, makeRegisterAuthResponse, routes.register.begin],
    ].forEach(([flow, makeResponse, beginRoute]) => {
      it(`sends the user back to the start of the ${flow} flow when the session expired`, () => {
        handleAuthResponse(
          history,
          makeResponse({ state: STATE_SESSION_EXPIRED }),
          {},
        );

        assert.equal(history.location.pathname, beginRoute);
      });
    });
  });
});
