// @flow
import React from "react";
import { assert } from "chai";
import { Redirect } from "react-router-dom";

import PrivateRoute, {
  PrivateRoute as InnerPrivateRoute,
} from "./PrivateRoute";
import IntegrationTestHelper from "../util/integration_test_helper";
import { routes } from "../lib/urls";
import { isIf } from "../lib/test_utils";
import { makeUser, makeAnonymousUser } from "../factories/user";

describe("PrivateRoute component", () => {
  let helper, renderComponent;

  const DummyComponent = () => <div>Dummy Component</div>;
  const fakeRoutePath = "/fake/path";
  const fakeWindowLocation = "/protected/route";
  const anonUser = makeAnonymousUser();
  const loggedInUser = makeUser();

  beforeEach(() => {
    helper = new IntegrationTestHelper();
    renderComponent = helper.configureHOCRenderer(
      PrivateRoute,
      InnerPrivateRoute,
      {},
      {},
    );
  });

  afterEach(() => {
    helper.cleanup();
  });
  [
    [false, loggedInUser, "load the route"],
    [true, anonUser, "redirect to the login page with a 'next' param"],
  ].forEach(([isAnonymous, user, desc]) => {
    it(`should ${desc} if user ${isIf(isAnonymous)} anonymous`, async () => {
      window.location = fakeWindowLocation;
      const { inner } = await renderComponent(
        {
          entities: {
            currentUser: user,
          },
        },
        {
          path: fakeRoutePath,
          component: DummyComponent,
        },
      );
      const routeComponent = inner.find("Route");
      assert.isTrue(routeComponent.exists());
      const { path, render } = routeComponent.props();
      assert.equal(path, fakeRoutePath);
      const renderResult = render();
      if (isAnonymous) {
        assert.equal(renderResult.type, Redirect);
        assert.equal(
          renderResult.props.to,
          `${routes.login.begin}?next=%2Fprotected%2Froute`,
        );
      } else {
        assert.equal(renderResult.type, DummyComponent);
      }
    });
  });
});
