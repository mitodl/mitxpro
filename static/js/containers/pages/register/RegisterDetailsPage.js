// @flow
import React from "react"
import { compose } from "redux"
import { connect } from "react-redux"
import { connectRequest, mutateAsync, requestAsync } from "redux-query"
import { createStructuredSelector } from "reselect"

import auth from "../../../lib/queries/auth"
import users from "../../../lib/queries/users"
import { routes } from "../../../lib/urls"
import { STATE_SUCCESS } from "../../../lib/auth"
import queries from "../../../lib/queries"
import { qsPartialTokenSelector } from "../../../lib/selectors"

import RegisterDetailsForm from "../../../components/forms/RegisterDetailsForm"

import type { RouterHistory, Location } from "react-router"
import type { Response } from "redux-query"
import type { AuthResponse, LegalAddress, User, Country } from "../../../flow/authTypes"

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

class RegisterProfilePage extends React.Component<Props> {
  async onSubmit(detailsData, { setSubmitting, setErrors }) {
    const {
      registerDetails,
      params: { partialToken }
    } = this.props

    try {
      const {
        body: { state, errors }
      }: { body: AuthResponse } = await registerDetails(
        detailsData.name,
        detailsData.password,
        detailsData.legal_address,
        partialToken
      )

      if (state === STATE_SUCCESS) {
        window.location.href = routes.root
      } else if (errors.length > 0) {
        setErrors({
          email: errors[0]
        })
      }
    } finally {
      setSubmitting(false)
    }
  }

  render() {
    const { countries } = this.props
    return (
      <div>
        <RegisterDetailsForm
          onSubmit={this.onSubmit.bind(this)}
          countries={countries}
        />
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
  connect(
    mapStateToProps,
    mapDispatchToProps
  ),
  connectRequest(mapPropsToConfig)
)(RegisterProfilePage)
