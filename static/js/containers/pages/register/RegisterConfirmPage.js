// @flow
/* global SETTINGS: false */
import React from "react";
import DocumentTitle from "react-document-title";
import { REGISTER_CONFIRM_PAGE_TITLE } from "../../../constants";
import { compose } from "redux";
import { connect } from "react-redux";
import { mutateAsync, connectRequest } from "redux-query";
import { path } from "ramda";
import { Link } from "react-router-dom";
import { createStructuredSelector } from "reselect";

import { addUserNotification } from "../../../actions";
import { ALERT_TYPE_TEXT } from "../../../constants";
import queries from "../../../lib/queries";
import { getAppropriateInformationFragment } from "../../../lib/util";
import {
  STATE_REGISTER_CONFIRM_REQUIRED,
  STATE_REGISTER_DETAILS,
  handleAuthResponse,
  INFORMATIVE_STATES,
} from "../../../lib/auth";
import { routes } from "../../../lib/urls";

import { authSelector } from "../../../lib/queries/auth";
import {
  qsVerificationCodeSelector,
  qsPartialTokenSelector,
  qsSelector,
} from "../../../lib/selectors";

import type { RouterHistory, Location } from "react-router";
import type { AuthResponse } from "../../../flow/authTypes";

type Props = {
  addUserNotification: Function,
  continueRegistration: Function,
  location: Location,
  history: RouterHistory,
  auth: ?AuthResponse,
  qsParams: Object,
};

type State = {
  continuing: boolean,
};

export class RegisterConfirmPage extends React.Component<Props, State> {
  state = { continuing: false };

  // set synchronously, so a fast double click can't send the one-time code twice
  continuing = false;

  mounted = false;

  componentDidMount() {
    this.mounted = true;
  }

  componentWillUnmount() {
    this.mounted = false;
  }

  componentDidUpdate(prevProps: Props) {
    const { addUserNotification, auth, history } = this.props;
    const prevState = path(["auth", "state"], prevProps);

    if (auth && auth.state !== prevState) {
      handleAuthResponse(history, auth, {
        [STATE_REGISTER_DETAILS]: () => {
          addUserNotification({
            "email-verified": {
              type: ALERT_TYPE_TEXT,
              props: {
                text: "Success! We've verified your email. Please finish your account creation below.",
              },
            },
          });
        },
      });
    }
  }

  onContinue = async () => {
    const { auth, continueRegistration, qsParams } = this.props;
    const nonce = path(["extra_data", "confirmation_nonce"], auth);
    if (!nonce || this.continuing) {
      return;
    }
    this.continuing = true;
    this.setState({ continuing: true });
    try {
      await continueRegistration(qsParams, nonce);
    } finally {
      this.continuing = false;
      if (this.mounted) {
        this.setState({ continuing: false });
      }
    }
  };

  renderConfirmRequired() {
    const { auth } = this.props;
    const email = path(["extra_data", "email"], auth);

    return (
      <div className="confirm-required">
        <h1>Confirm your email</h1>
        <p className="confirmation-message">
          Continue creating your account for <strong>{email}</strong>?
        </p>
        <button
          type="button"
          className="btn btn-primary btn-light-blue"
          onClick={this.onContinue}
          disabled={this.state.continuing}
        >
          Continue
        </button>
        <p className="not-my-email mt-3">
          Not your email?{" "}
          <Link className="action-link" to={routes.register.begin}>
            Create an account with a different email
          </Link>
          .
        </p>
      </div>
    );
  }

  renderContent() {
    const { auth } = this.props;

    if (auth && auth.state === STATE_REGISTER_CONFIRM_REQUIRED) {
      return this.renderConfirmRequired();
    }
    if (auth && INFORMATIVE_STATES.indexOf(auth.state) > -1) {
      return getAppropriateInformationFragment(auth.state);
    }
    return <p>Confirming...</p>;
  }

  render() {
    return (
      <DocumentTitle
        title={`${SETTINGS.site_name} | ${REGISTER_CONFIRM_PAGE_TITLE}`}
      >
        <div className="container auth-page">
          <div className="row">
            <div className="col">{this.renderContent()}</div>
          </div>
        </div>
      </DocumentTitle>
    );
  }
}

const mapStateToProps = createStructuredSelector({
  auth: authSelector,
  qsParams: qsSelector,
});

const mapPropsToConfig = ({ qsParams }) =>
  mutateAsync(queries.auth.registerConfirmEmailMutation(qsParams));

const continueRegistration = (qsParams: Object, confirmationNonce: string) =>
  mutateAsync(
    queries.auth.registerConfirmEmailContinueMutation(
      qsParams,
      confirmationNonce,
    ),
  );

const mapDispatchToProps = {
  addUserNotification,
  continueRegistration,
};

export default compose(
  connect(mapStateToProps, mapDispatchToProps),
  connectRequest(mapPropsToConfig),
)(RegisterConfirmPage);
