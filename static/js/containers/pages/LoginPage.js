// @flow
import React from "react"
import { compose } from "redux"
import { connect } from "react-redux"
import { mutateAsync } from "redux-query"

import queries from "../../lib/queries"
import { routes, getNextParam } from "../../lib/urls"
import { STATE_SUCCESS, STATE_LOGIN_PASSWORD } from "../../lib/auth"

import { LoginEmailForm, LoginPasswordForm } from "../../components/forms/login"

import type { RouterHistory, Location } from "react-router"
import type { Response } from "redux-query"
import type { AuthResponse } from "../../flow/authTypes"

const STEP_EMAIL = "email"
const STEP_PASSWORD = "password"

type Props = {
  location: Location,
  history: RouterHistory,
  loginEmail: (email: string, next: ?string) => Promise<Response<AuthResponse>>,
  loginPassword: (
    password: string,
    partialToken: string
  ) => Promise<Response<AuthResponse>>
}

type State = {
  step: "email" | "password",
  partialToken: ?string,
  name: ?string
}

class LoginPage extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = {
      step:         STEP_EMAIL,
      partialToken: null,
      name:         null
    }
  }

  async onSubmitEmail({ email }, { setSubmitting, setErrors }) {
    const { loginEmail, location } = this.props
    const nextUrl = getNextParam(location.search)

    /* eslint-disable camelcase */
    try {
      const {
        body: { state, partial_token, errors, extra_data }
      }: { body: AuthResponse } = await loginEmail(email, nextUrl)

      if (state === STATE_LOGIN_PASSWORD) {
        this.setState({
          step:         STEP_PASSWORD,
          partialToken: partial_token,
          name:         extra_data.name
        })
      } else if (errors.length > 0) {
        setErrors({
          email: errors[0]
        })
      }
    } finally {
      setSubmitting(false)
    }
    /* eslint-enable camelcase */
  }

  async onSubmitPassword({ password }, { setSubmitting, setErrors }) {
    const { loginPassword, history } = this.props
    const { partialToken } = this.state

    if (!partialToken) {
      throw Error("Invalid state: password page with no partialToken")
    }

    /* eslint-disable camelcase */
    try {
      const {
        body: { state, redirect_url, errors }
      }: { body: AuthResponse } = await loginPassword(password, partialToken)

      if (state === STATE_SUCCESS) {
        history.push(redirect_url || routes.home)
      } else if (errors.length > 0) {
        setErrors({
          password: errors[0]
        })
      }
    } finally {
      setSubmitting(false)
    }
    /* eslint-enable camelcase */
  }

  render() {
    const { step, name } = this.state

    let stepForm = null

    if (step === STEP_EMAIL) {
      stepForm = <LoginEmailForm onSubmit={this.onSubmitEmail.bind(this)} />
    } else if (step === STEP_PASSWORD) {
      stepForm = (
        <React.Fragment>
          <p>Logging in as {name}</p>
          <LoginPasswordForm onSubmit={this.onSubmitPassword.bind(this)} />
        </React.Fragment>
      )
    }

    return <div>{stepForm}</div>
  }
}

const loginEmail = (email: string, nextUrl: ?string) =>
  mutateAsync(queries.auth.loginEmailMutation(email, nextUrl))
const loginPassword = (password: string, partialToken: string) =>
  mutateAsync(queries.auth.loginPasswordMutation(password, partialToken))

const mapDispatchToProps = {
  loginEmail,
  loginPassword
}

export default compose(
  connect(
    null,
    mapDispatchToProps
  )
)(LoginPage)
