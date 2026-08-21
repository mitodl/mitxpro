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
  attempts: number,
};

// Stripe sends nothing to this page; the order is fulfilled by a webhook that
// usually lands a moment after the learner gets back here. Poll until it does,
// then move them on. Give up after a while rather than spinning forever -- the
// order is still recoverable server-side, and a stuck spinner helps nobody.
const NUM_MILLIS_PER_POLL = 2000;
const MAX_ATTEMPTS = 30;

export class CheckoutResultPage extends React.Component<Props, State> {
  state = {
    attempts: 0,
  };

  componentDidUpdate(prevProps: Props) {
    if (prevProps.orderStatus !== this.props.orderStatus) {
      this.handleOrderStatus();
    }
  }

  componentDidMount() {
    this.handleOrderStatus();
  }

  receiptUrl = () => {
    const purchased = qs.parse(this.props.location.search).purchased;
    return purchased
      ? `${routes.dashboard}?status=purchased&purchased=${encodeURIComponent(
          String(purchased),
        )}`
      : routes.dashboard;
  };

  handleOrderStatus = async () => {
    const { orderStatus, forceRequest } = this.props;
    const { attempts } = this.state;

    if (!orderStatus) {
      // wait until we have an order status
      return;
    }

    if (orderStatus.status === "fulfilled") {
      window.location = this.receiptUrl();
      return;
    }

    if (orderStatus.status === "failed" || attempts >= MAX_ATTEMPTS) {
      return;
    }

    this.setState({ attempts: attempts + 1 });
    await wait(NUM_MILLIS_PER_POLL);
    await forceRequest();
  };

  render() {
    const { orderStatus } = this.props;
    const failed = orderStatus && orderStatus.status === "failed";

    return (
      <div className="container checkout-result" style={{ padding: "4rem 0" }}>
        {failed ? (
          <React.Fragment>
            <h2>We couldn&rsquo;t complete your payment</h2>
            <p>
              Your card was not charged. Please try again, or contact support if
              the problem continues.
            </p>
            <a href={routes.dashboard}>Return to your dashboard</a>
          </React.Fragment>
        ) : (
          <React.Fragment>
            <h2>Completing your purchase&hellip;</h2>
            <p>
              Your payment went through. We&rsquo;re finalizing your enrollment
              &mdash; this usually takes a few seconds.
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
