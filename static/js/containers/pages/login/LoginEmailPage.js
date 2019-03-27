// @flow
import React from "react"
import { compose } from "redux"
import { connect } from "react-redux"
import { mutateAsync } from "redux-query"

import auth from "../../../lib/queries/auth"
import { routes, getNextParam } from "../../../lib/urls"
import { STATE_LOGIN_PASSWORD } from "../../../lib/auth"

import { LoginEmailForm } from "../../../components/forms/login"

import type { RouterHistory, Location } from "react-router"
import type { Response } from "redux-query"
import type { AuthResponse } from "../../../flow/authTypes"

type Props = {
  location: Location,
  history: RouterHistory,
  loginEmail: (email: string, next: ?string) => Promise<Response<AuthResponse>>
}

class LoginEmailPage extends React.Component<Props> {
  async onSubmit({ email }, { setSubmitting, setErrors }) {
    const { loginEmail, location, history } = this.props
    const nextUrl = getNextParam(location.search)

    /* eslint-disable camelcase */
    try {
      const result = await loginEmail(email, nextUrl)
      const { state, errors } = result.transformed.auth

      if (state === STATE_LOGIN_PASSWORD) {
        history.push(routes.login.password)
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

  render() {
    return (
      <div>
        <LoginEmailForm onSubmit={this.onSubmit.bind(this)} />
      </div>
    )
  }
}

const loginEmail = (email: string, nextUrl: ?string) =>
  mutateAsync(auth.loginEmailMutation(email, nextUrl))

const mapDispatchToProps = {
  loginEmail
}

export default compose(
  connect(
    null,
    mapDispatchToProps
  )
)(LoginEmailPage)
