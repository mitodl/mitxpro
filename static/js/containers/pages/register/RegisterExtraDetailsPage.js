// @flow
import React from "react"
import { compose } from "redux"
import { connect } from "react-redux"
import { Link } from "react-router-dom"
import { mutateAsync, requestAsync } from "redux-query"
import { createStructuredSelector } from "reselect"

import { STATE_SUCCESS } from "../../../lib/auth"
import auth from "../../../lib/queries/auth"
import users from "../../../lib/queries/users"
import { routes } from "../../../lib/urls"
import { qsPartialTokenSelector } from "../../../lib/selectors"

import RegisterExtraDetailsForm from "../../../components/forms/RegisterExtraDetailsForm"

import type { RouterHistory, Location } from "react-router"
import type { Response } from "redux-query"
import type { AuthResponse, User, UserProfile } from "../../../flow/authTypes"

type RegisterProps = {|
  location: Location,
  history: RouterHistory,
  params: { partialToken: string }
|}

type DispatchProps = {|
  registerExtraDetails: (
    profileData: UserProfile,
    partialToken: string
  ) => Promise<Response<AuthResponse>>,
  getCurrentUser: () => Promise<Response<User>>
|}

type Props = {|
  ...RegisterProps,
  ...DispatchProps
|}

class RegisterExtraDetailsPage extends React.Component<Props> {
  async onSubmit(profileData, { setSubmitting, setErrors }) {
    const {
      registerExtraDetails,
      params: { partialToken }
    } = this.props

    try {
      const {
        body: { state, errors }
      }: { body: AuthResponse } = await registerExtraDetails(
        profileData,
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
    return (
      <div className="registration-form">
        <div className="form-group row">
          <h3 className="col-8">Create an Account</h3>
          <h5 className="col-4 align-text-right gray-text">Step 2 of 2</h5>
        </div>
        <div className="form-group row">
          <div className="col">
            Already have an MITxPro account?{" "}
            <Link to={routes.login.begin}>Click here</Link>
          </div>
        </div>
        <div className="inner-form">
          <RegisterExtraDetailsForm onSubmit={this.onSubmit.bind(this)} />
        </div>
      </div>
    )
  }
}

const mapStateToProps = createStructuredSelector({
  params: createStructuredSelector({ partialToken: qsPartialTokenSelector })
})

const registerExtraDetailsPage = (
  profileData: UserProfile,
  partialToken: string
) => mutateAsync(auth.registerExtraDetailsMutation(profileData, partialToken))

const getCurrentUser = () =>
  requestAsync({
    ...users.currentUserQuery(),
    force: true
  })

const mapDispatchToProps = {
  registerExtraDetails: registerExtraDetailsPage,
  getCurrentUser
}

export default compose(
  connect(
    mapStateToProps,
    mapDispatchToProps
  )
)(RegisterExtraDetailsPage)
