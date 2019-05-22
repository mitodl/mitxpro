// @flow
import React from "react"
import { compose } from "redux"
import { connect } from "react-redux"
import { mutateAsync, requestAsync } from "redux-query"
import { createStructuredSelector } from "reselect"

import auth, { authSelector } from "../../../lib/queries/auth"
import users from "../../../lib/queries/users"
import { routes } from "../../../lib/urls"
import { STATE_SUCCESS } from "../../../lib/auth"

import LoginPasswordForm from "../../../components/forms/LoginPasswordForm"

import type { RouterHistory, Location } from "react-router"
import type { Response } from "redux-query"
import type { AuthResponse, User } from "../../../flow/authTypes"

type Props = {
  location: Location,
  history: RouterHistory,
  auth: AuthResponse,
  loginPassword: (
    password: string,
    partialToken: string
  ) => Promise<Response<AuthResponse>>,
  getCurrentUser: () => Promise<Response<User>>
}

class LoginPasswordPage extends React.Component<Props> {
  componentDidMount() {
    const { history, auth } = this.props

    if (!auth || !auth.partialToken) {
      // if there's no partialToken in the state
      // this page was navigated to directly and login needs to be started over
      history.push(routes.login.begin)
    }
  }

  async onSubmit({ password }, { setSubmitting, setErrors }) {
    const {
      loginPassword,
      auth: { partialToken }
    } = this.props

    if (!partialToken) {
      throw Error("Invalid state: password page with no partialToken")
    }

    try {
      const {
        body: { state, redirectUrl, errors }
      }: { body: AuthResponse } = await loginPassword(password, partialToken)

      if (state === STATE_SUCCESS) {
        window.location.href = redirectUrl || routes.dashboard
      } else if (errors.length > 0) {
        setErrors({
          password: errors[0]
        })
      }
    } finally {
      setSubmitting(false)
    }
  }

  render() {
    const { auth } = this.props

    if (!auth) {
      return <div />
    }

    const name = auth.extraData.name

    return (
      <div className="container auth-page">
        <div className="row auth-header">
          <h1 className="col-12">Login</h1>
        </div>
        <div className="row auth-card card-shadow auth-form">
          {name && (
            <div className="col-12">
              <p>Logging in as {name}</p>
            </div>
          )}
          <div className="col-12">
            <LoginPasswordForm onSubmit={this.onSubmit.bind(this)} />
          </div>
        </div>
      </div>
    )
  }
}

const mapStateToProps = createStructuredSelector({
  auth: authSelector
})

const loginPassword = (password: string, partialToken: string) =>
  mutateAsync(auth.loginPasswordMutation(password, partialToken))

const getCurrentUser = () =>
  requestAsync({
    ...users.currentUserQuery(),
    force: true
  })

const mapDispatchToProps = {
  loginPassword,
  getCurrentUser
}

export default compose(
  connect(
    mapStateToProps,
    mapDispatchToProps
  )
)(LoginPasswordPage)
