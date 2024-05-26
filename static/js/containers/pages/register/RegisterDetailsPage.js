// @flow
/* global SETTINGS: false */
import React from "react";
import DocumentTitle from "react-document-title";
import { ALERT_TYPE_DANGER, REGISTER_DETAILS_PAGE_TITLE } from "../../../constants";
import { compose } from "redux";
import { connect } from "react-redux";
import { Link } from "react-router-dom";
import { connectRequest, mutateAsync, requestAsync } from "redux-query";
import { createStructuredSelector } from "reselect";

import { authSelector } from "../../../lib/queries/auth";
import auth from "../../../lib/queries/auth";
import users from "../../../lib/queries/users";
import { routes } from "../../../lib/urls";
import { getAppropriateInformationFragment } from "../../../lib/util";
import {
  STATE_ERROR,
  STATE_EXISTING_ACCOUNT,
  handleAuthResponse,
} from "../../../lib/auth";
import queries from "../../../lib/queries";
import { qsPartialTokenSelector } from "../../../lib/selectors";

import RegisterDetailsForm from "../../../components/forms/RegisterDetailsForm";

import type { RouterHistory, Location } from "react-router";
import type { Response } from "redux-query";
import type {
  AuthResponse,
  LegalAddress,
  User,
  Country,
} from "../../../flow/authTypes";
import { addUserNotification } from "../../../actions"

type RegisterProps = {|
  location: Location,
  history: RouterHistory,
  authResponse: ?AuthResponse,
  params: { partialToken: string },
|};

type StateProps = {|
  countries: Array<Country>,
|};

type DispatchProps = {|
  registerDetails: (
    name: string,
    password: string,
    legalAddress: LegalAddress,
    partialToken: string,
  ) => Promise<Response<AuthResponse>>,
  getCurrentUser: () => Promise<Response<User>>,
  addUserNotification: Function,
|};

type Props = {|
  ...RegisterProps,
  ...StateProps,
  ...DispatchProps,
|};

type State = {
  isVatEnabled: boolean,
};

export class RegisterDetailsPage extends React.Component<Props, State> {
  state = {
    isVatEnabled: false,
  };

  async onSubmit(detailsData: any, { setSubmitting, setErrors }: any) {
    const {
      history,
      registerDetails,
      params: { partialToken },
      addUserNotification,
    } = this.props;

    try {
      const { body } = await registerDetails(
        detailsData.name,
        detailsData.password,
        detailsData.legal_address,
        partialToken,
      );

      if (body.errors) {
        body.errors.forEach(error => {
          addUserNotification({
            "registration-failed-status": {
              type:  ALERT_TYPE_DANGER,
              props: {
                text: error
              }
            }
          })
        })
      }

      handleAuthResponse(history, body, {
        // eslint-disable-next-line camelcase
        [STATE_ERROR]: ({ field_errors }: AuthResponse) =>
          setErrors(field_errors),
      });
    } finally {
      setSubmitting(false);
    }
  }

  enableVatID = () => this.setState({ isVatEnabled: true });

  render() {
    const { authResponse, countries } = this.props;

    return (
      <DocumentTitle
        title={`${SETTINGS.site_name} | ${REGISTER_DETAILS_PAGE_TITLE}`}
      >
        {authResponse && authResponse.state === STATE_EXISTING_ACCOUNT ? (
          <div className="container auth-page registration-page">
            <div className="auth-header row d-flex flex-row align-items-center justify-content-between flex-nowrap">
              <div className="col-auto flex-shrink-1">
                {getAppropriateInformationFragment(authResponse.state)}
              </div>
            </div>
          </div>
        ) : (
          <div className="container auth-page registration-page">
            <div className="auth-header row d-flex flex-row align-items-center justify-content-between flex-nowrap">
              <div className="col-auto flex-shrink-1">
                <h1>Create an Account</h1>
              </div>
              <div className="col-auto align-text-right gray-text">
                <h4>Step 1 of 2</h4>
              </div>
            </div>
            <div className="auth-card card-shadow row">
              <div className="container">
                <div className="row">
                  <div className="col-12 form-group">
                    {`Already have an ${SETTINGS.site_name} account? `}
                    <Link to={routes.login.begin}>Click here</Link>
                  </div>
                </div>
                <div className="row">
                  <div className="col-12 auth-form">
                    <RegisterDetailsForm
                      onSubmit={this.onSubmit.bind(this)}
                      countries={countries}
                      isVatEnabled={this.state.isVatEnabled}
                      enableVatID={this.enableVatID.bind(this)}
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </DocumentTitle>
    );
  }
}

const mapStateToProps = createStructuredSelector({
  authResponse: authSelector,
  params: createStructuredSelector({ partialToken: qsPartialTokenSelector }),
  countries: queries.users.countriesSelector,
});

const mapPropsToConfig = () => [queries.users.countriesQuery()];

const registerDetails = (
  name: string,
  password: string,
  legalAddress: LegalAddress,
  partialToken: string,
) =>
  mutateAsync(
    auth.registerDetailsMutation(name, password, legalAddress, partialToken),
  );

const getCurrentUser = () =>
  requestAsync({
    ...users.currentUserQuery(),
    force: true,
  });

const mapDispatchToProps = {
  registerDetails,
  getCurrentUser,
  addUserNotification,
};

export default compose(
  connect(mapStateToProps, mapDispatchToProps),
  connectRequest(mapPropsToConfig),
)(RegisterDetailsPage);
