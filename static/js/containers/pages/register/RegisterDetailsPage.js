// @flow
/* global SETTINGS: false */
import React from "react"
import DocumentTitle from "react-document-title"
import { REGISTER_DETAILS_PAGE_TITLE } from "../../../constants"
import { compose } from "redux"
import { connect } from "react-redux"
import { Link } from "react-router-dom"
import { connectRequest, mutateAsync, requestAsync } from "redux-query"
import { createStructuredSelector } from "reselect"

import auth from "../../../lib/queries/auth"
import users from "../../../lib/queries/users"
import { routes } from "../../../lib/urls"
import { STATE_ERROR, handleAuthResponse } from "../../../lib/auth"
import queries from "../../../lib/queries"
import { qsPartialTokenSelector } from "../../../lib/selectors"

import RegisterDetailsForm from "../../../components/forms/RegisterDetailsForm"

import type { RouterHistory, Location } from "react-router"
import type { Response } from "redux-query"
import type {
  AuthResponse,
  LegalAddress,
  User,
  Country
} from "../../../flow/authTypes"

type RegisterProps = {|
  location: Location,
  history: RouterHistory,
  params: { partialToken: string }
|}

type StateProps = {|
  countries: Array<Country>
|}

type DispatchProps = {|
  registerDetails: (
    name: string,
    password: string,
    legalAddress: LegalAddress,
    partialToken: string
  ) => Promise<Response<AuthResponse>>,
  getCurrentUser: () => Promise<Response<User>>
|}

type Props = {|
  ...RegisterProps,
  ...StateProps,
  ...DispatchProps
|}

export class RegisterDetailsPage extends React.Component<Props> {
  async onSubmit(detailsData: any, { setSubmitting, setErrors }: any) {
    const {
      history,
      registerDetails,
      params: { partialToken }
    } = this.props

    try {
      const { body } = await registerDetails(
        detailsData.name,
        detailsData.password,
        detailsData.legal_address,
        partialToken
      )

      handleAuthResponse(history, body, {
        // eslint-disable-next-line camelcase
        [STATE_ERROR]: ({ field_errors }: AuthResponse) =>
          setErrors(field_errors)
      })
    } finally {
      setSubmitting(false)
    }
  }

  render() {
    const { countries } = this.props

    return (
      <DocumentTitle
        title={`${SETTINGS.site_name} | ${REGISTER_DETAILS_PAGE_TITLE}`}
      >
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
                  />
                </div>
              </div>
            </div>
          </div>
        </div>
      </DocumentTitle>
    )
  }
}

const mapStateToProps = createStructuredSelector({
  params:    createStructuredSelector({ partialToken: qsPartialTokenSelector }),
  countries: queries.users.countriesSelector
})

const mapPropsToConfig = () => [queries.users.countriesQuery()]

const registerDetails = (
  name: string,
  password: string,
  legalAddress: LegalAddress,
  partialToken: string
) =>
  mutateAsync(
    auth.registerDetailsMutation(name, password, legalAddress, partialToken)
  )

const getCurrentUser = () =>
  requestAsync({
    ...users.currentUserQuery(),
    force: true
  })

const mapDispatchToProps = {
  registerDetails,
  getCurrentUser
}

export default compose(
  connect(
    mapStateToProps,
    mapDispatchToProps
  ),
  connectRequest(mapPropsToConfig)
)(RegisterDetailsPage)
