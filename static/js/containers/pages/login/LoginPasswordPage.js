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

import { LoginPasswordForm } from "../../../components/forms/login"

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
    const {
      history,
      auth: { partialToken }
    } = this.props

    if (!partialToken) {
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
        window.location.href = redirectUrl || routes.root
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
    const {
      auth: {
        extraData: { name }
      }
    } = this.props

    return (
      <div>
        <p>Logging in as {name}</p>
        <LoginPasswordForm onSubmit={this.onSubmit.bind(this)} />
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
