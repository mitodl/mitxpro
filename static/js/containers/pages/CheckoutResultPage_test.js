// @flow
import { assert } from "chai";

import CheckoutResultPage, {
  CheckoutResultPage as InnerCheckoutResultPage,
} from "./CheckoutResultPage";
import IntegrationTestHelper from "../../util/integration_test_helper";

describe("CheckoutResultPage", () => {
  let helper, renderPage;

  beforeEach(() => {
    helper = new IntegrationTestHelper();
    renderPage = helper.configureHOCRenderer(
      CheckoutResultPage,
      InnerCheckoutResultPage,
      {
        entities: { stripe_order_status: null },
      },
      {
        location: {
          search:
            "?session_id=cs_test_123&purchased=course-v1%3ATestX%2BB1%2BR1",
        },
      },
    );
  });

  afterEach(() => {
    helper.cleanup();
  });

  it("tells the learner we're finishing up while the webhook lands", async () => {
    const { inner } = await renderPage({
      entities: { stripe_order_status: { status: "created" } },
    });

    assert.include(inner.text(), "Completing your purchase");
  });

  it("shows an error if the payment failed", async () => {
    const { inner } = await renderPage({
      entities: { stripe_order_status: { status: "failed" } },
    });

    assert.include(inner.text(), "couldn’t complete your payment");
  });

  it("sends the learner to their dashboard once the order is fulfilled", async () => {
    await renderPage({
      entities: { stripe_order_status: { status: "fulfilled" } },
    });

    assert.include(window.location.toString(), "status=purchased");
  });
});
