// @flow
/* global SETTINGS: false */
import React from "react"
import { compose } from "redux"
import { connect } from "react-redux"
import { Link } from "react-router-dom"
import { isEmpty } from "ramda"
import { connectRequest, mutateAsync, requestAsync } from "redux-query"
import { createStructuredSelector } from "reselect"
import qs from "query-string"

import auth from "../../../lib/queries/auth"
import users from "../../../lib/queries/users"
import { routes, RedirectToRegister } from "../../../lib/urls"
import {
  STATE_REGISTER_EXTRA_DETAILS,
  STATE_USER_BLOCKED,
  STATE_ERROR
} from "../../../lib/auth"
import queries from "../../../lib/queries"
import { qsPartialTokenSelector } from "../../../lib/selectors"

import RegisterDetailsForm from "../../../components/forms/RegisterDetailsForm"
import withRequiredQueryParams from "../../../hoc/withRequiredQueryParams"

import type { RouterHistory, Location } from "react-router"
import type { Response } from "redux-query"
import type {
  AuthResponse,
  AuthResponseRaw,
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
      const {
        body: { state, errors, partial_token } // eslint-disable-line camelcase
      }: { body: AuthResponseRaw } = await registerDetails(
        detailsData.name,
        detailsData.password,
        detailsData.legal_address,
        partialToken
      )

      if (state === STATE_REGISTER_EXTRA_DETAILS) {
        const params = qs.stringify({
          partial_token
        })
        history.push(`${routes.register.extra}?${params}`)
      } else if (state === STATE_USER_BLOCKED) {
        const params = !isEmpty(errors)
          ? qs.stringify({
            error: errors[0]
          })
          : ""
        history.push(`${routes.register.denied}?${params}`)
      } else if (state === STATE_ERROR && errors.length > 0) {
        setErrors({
          name: errors[0]
        })
      } else {
        // otherwise we're in some kind of error state, explicit or otherwise
        history.push(routes.register.error)
      }
    } finally {
      setSubmitting(false)
    }
  }

  render() {
    const { countries } = this.props

    return (
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
                Already have an MITxPro account?{" "}
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
  withRequiredQueryParams(["partial_token"], RedirectToRegister),
  connect(
    mapStateToProps,
    mapDispatchToProps
  ),
  connectRequest(mapPropsToConfig)
)(RegisterDetailsPage)
