// @flow
import { assert } from "chai";
import sinon from "sinon";
import { mergeRight } from "ramda";
import { Switch, matchPath } from "react-router";

import App, { App as InnerApp } from "./App";
import { routes } from "../lib/urls";
import IntegrationTestHelper from "../util/integration_test_helper";
import { makeUser, makeUnusedCoupon } from "../factories/user";
import { ALERT_TYPE_UNUSED_COUPON } from "../constants";
import DashboardPage from "./pages/DashboardPage";
import ReceiptPage from "./pages/ReceiptPage";
import LoginPages from "./pages/login/LoginPages";
import RegisterPages from "./pages/register/RegisterPages";
import CheckoutPage from "./pages/CheckoutPage";
import CheckoutResultPage from "./pages/CheckoutResultPage";
import EcommerceAdminPages from "./pages/admin/EcommerceAdminPages";
import ProfilePages from "./pages/profile/ProfilePages";
import EcommerceBulkPages from "./pages/b2b/EcommerceBulkPages";
import AccountSettingsPage from "./pages/settings/AccountSettingsPage";
import EmailConfirmPage from "./pages/settings/EmailConfirmPage";

describe("Top-level App", () => {
  let helper, renderPage;

  beforeEach(() => {
    helper = new IntegrationTestHelper();
    renderPage = helper.configureHOCRenderer(
      App,
      InnerApp,
      {},
      {
        match: { url: routes.root },
        location: {
          pathname: routes.root,
        },
      },
    );
  });

  afterEach(() => {
    helper.cleanup();
  });

  it("fetches user data on load and initially renders an empty element", async () => {
    const { inner } = await renderPage();

    assert.notExists(inner.find(".app").prop("children"));
    sinon.assert.calledWith(helper.handleRequestStub, "/api/users/me", "GET");
  });

  describe("unused coupon alert", () => {
    let userWithUnusedCoupons, unusedCoupon, expectedNotificationState;

    beforeEach(() => {
      unusedCoupon = makeUnusedCoupon();
      userWithUnusedCoupons = mergeRight(makeUser(), {
        unused_coupons: [unusedCoupon],
      });
      expectedNotificationState = {
        "unused-coupon": {
          type: ALERT_TYPE_UNUSED_COUPON,
          props: {
            productId: unusedCoupon.product_id,
            couponCode: unusedCoupon.coupon_code,
          },
        },
      };
    });

    it("is triggered if the user is loaded and has unused coupons", async () => {
      const { inner, store } = await renderPage();

      inner.setProps({ currentUser: userWithUnusedCoupons });

      const { ui } = store.getState();
      assert.deepEqual(ui.userNotifications, expectedNotificationState);
    });

    it("is triggered if the user changes from the checkout page to another page", async () => {
      let state;
      const { inner, store } = await renderPage(
        {},
        {
          location: { pathname: routes.checkout },
        },
      );

      inner.setProps({ currentUser: userWithUnusedCoupons });
      state = store.getState();
      assert.deepEqual(state.ui.userNotifications, {});

      inner.setProps({ location: { pathname: routes.dashboard } });
      state = store.getState();
      assert.deepEqual(state.ui.userNotifications, expectedNotificationState);
    });
  });

  describe("routing", () => {
    // Mirror <Switch>: the first child whose path matches the URL wins
    const matchedComponent = (inner, url) => {
      const route = inner
        .find(Switch)
        .children()
        .filterWhere((child) =>
          matchPath(url, {
            path: child.prop("path"),
            exact: child.prop("exact"),
          }),
        )
        .first();
      return route.exists() ? route.prop("component") : null;
    };

    [
      [routes.dashboard, DashboardPage],
      ["/receipt/123/", ReceiptPage],
      [routes.login.begin, LoginPages],
      [routes.login.password, LoginPages],
      [routes.register.details, RegisterPages],
      [routes.checkoutResult, CheckoutResultPage],
      [routes.checkout, CheckoutPage],
      [routes.ecommerceAdmin.coupons, EcommerceAdminPages],
      [routes.profile.update, ProfilePages],
      [routes.ecommerceBulk.receipt, EcommerceBulkPages],
      [routes.accountSettings, AccountSettingsPage],
      [routes.account.confirmEmail, EmailConfirmPage],
    ].forEach(([url, expectedComponent]) => {
      it(`routes ${url} to the right page`, async () => {
        const { inner } = await renderPage();
        inner.setProps({ currentUser: makeUser() });

        assert.equal(matchedComponent(inner, url), expectedComponent);
      });
    });
  });
});
