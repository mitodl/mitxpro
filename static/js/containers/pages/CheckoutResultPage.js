// @flow
import React from "react";
import { connect } from "react-redux";
import { compose } from "redux";
import { connectRequest } from "redux-query";
import qs from "query-string";

import queries from "../../lib/queries";
import { routes } from "../../lib/urls";
import { wait } from "../../lib/util";

import type { Location } from "react-router";

type Props = {
  orderStatus: ?Object,
  location: Location,
  forceRequest: () => Promise<void>,
};
type State = {
  timedOut: boolean,
};

// Stripe sends nothing to this page; the order is fulfilled by a webhook that
// usually lands a moment after the learner gets back here. Poll until it does,
// then move them on. Give up after a while rather than spinning forever -- the
// order is still recoverable server-side, and a stuck spinner helps nobody.
const NUM_MILLIS_PER_POLL = 2000;
const MAX_ATTEMPTS = 30;

export class CheckoutResultPage extends React.Component<Props, State> {
  state = {
    timedOut: false,
  };

  componentDidMount() {
    this.poll();
  }

  componentWillUnmount() {
    this.unmounted = true;
  }

  unmounted = false;

  receiptUrl = () => {
    const purchased = qs.parse(this.props.location.search).purchased;
    return purchased
      ? `${routes.dashboard}?status=purchased&purchased=${encodeURIComponent(
          String(purchased),
        )}`
      : routes.dashboard;
  };

  // Driven by a timer rather than by successful entity updates: if the first
  // status request fails there is no update to react to, and a learner who has
  // paid would sit here forever. Request errors are swallowed so a transient
  // failure doesn't break the chain.
  poll = async () => {
    for (let attempt = 0; attempt < MAX_ATTEMPTS; attempt++) {
      if (this.unmounted) {
        return;
      }

      const { orderStatus } = this.props;

      if (orderStatus && orderStatus.status === "fulfilled") {
        window.location = this.receiptUrl();
        return;
      }

      if (orderStatus && orderStatus.status === "failed") {
        return;
      }

      await wait(NUM_MILLIS_PER_POLL);

      try {
        await this.props.forceRequest();
      } catch (e) {
        // Keep polling: a transient error shouldn't strand a paid learner.
      }
    }

    if (!this.unmounted) {
      // Stop polling, but say so. Delayed payment methods legitimately stay
      // unconfirmed for far longer than this, and leaving "completing your
      // purchase" on screen forever implies something is still happening.
      this.setState({ timedOut: true });
    }
  };

  render() {
    const { orderStatus } = this.props;
    const { timedOut } = this.state;
    const failed = orderStatus && orderStatus.status === "failed";

    return (
      <div className="container checkout-result" style={{ padding: "4rem 0" }}>
        {failed ? (
          <React.Fragment>
            <h2>We couldn&rsquo;t complete your payment</h2>
            <p>
              You have not been charged. Please try again, or contact support if
              the problem continues.
            </p>
            <a href={routes.dashboard}>Return to your dashboard</a>
          </React.Fragment>
        ) : timedOut ? (
          <React.Fragment>
            <h2>Your payment is still being confirmed</h2>
            <p>
              This is normal for some payment methods, such as bank transfers,
              which can take a few days to clear. We&rsquo;ll email you as soon
              as it&rsquo;s confirmed and your enrollment is ready &mdash; you
              don&rsquo;t need to pay again or stay on this page.
            </p>
            <a href={routes.dashboard}>Go to your dashboard</a>
          </React.Fragment>
        ) : (
          <React.Fragment>
            <h2>Completing your purchase&hellip;</h2>
            <p>
              We&rsquo;re confirming your payment and finalizing your
              enrollment. This usually takes a few seconds, though some payment
              methods &mdash; bank transfers in particular &mdash; can take
              longer. We&rsquo;ll email you once it&rsquo;s confirmed.
            </p>
            <a href={this.receiptUrl()}>Continue to your dashboard</a>
          </React.Fragment>
        )}
      </div>
    );
  }
}

const mapStateToProps = (state) => ({
  orderStatus: state.entities.stripe_order_status,
});

const mapPropsToConfig = (props) => [
  queries.ecommerce.stripeOrderStatus(
    String(qs.parse(props.location.search).session_id || ""),
  ),
];

export default compose(
  connect(mapStateToProps),
  connectRequest(mapPropsToConfig),
)(CheckoutResultPage);
