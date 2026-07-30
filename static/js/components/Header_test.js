// @flow
import React from "react";
import { assert } from "chai";
import sinon from "sinon";
import { shallow } from "enzyme";
import posthog from "posthog-js";

import Header from "./Header";
import { makeUser, makeAnonymousUser } from "../factories/user";

describe("Header component", () => {
  let sandbox, identifyStub;

  beforeEach(() => {
    sandbox = sinon.createSandbox();
    identifyStub = sandbox.stub(posthog, "identify");
    global.SETTINGS = { environment: "test" };
  });

  afterEach(() => {
    sandbox.restore();
    delete global.SETTINGS;
  });

  const render = (currentUser) =>
    shallow(
      <Header
        currentUser={currentUser}
        location={null}
        errorPageHeader={false}
        courseTopics={[]}
      />,
    );

  it("identifies the user to PostHog with an xpro-prefixed id", () => {
    const user = makeUser();

    render(user);

    sinon.assert.calledWith(identifyStub, `xpro:${user.id}`, {
      environment: "test",
      user_id: user.id,
    });
  });

  it("does not identify an anonymous user", () => {
    render(makeAnonymousUser());

    sinon.assert.notCalled(identifyStub);
  });
});
