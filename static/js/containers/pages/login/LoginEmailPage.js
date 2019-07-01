// @flow
import React from "react"
import { compose } from "redux"
import { connect } from "react-redux"
import { mutateAsync } from "redux-query"

import auth from "../../../lib/queries/auth"
import { routes, getNextParam } from "../../../lib/urls"
import { STATE_LOGIN_PASSWORD } from "../../../lib/auth"

import EmailForm from "../../../components/forms/EmailForm"

import type { RouterHistory, Location } from "react-router"
import type { Response } from "redux-query"
import type { AuthResponse } from "../../../flow/authTypes"
import { Link } from "react-router-dom"

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
      <div className="container auth-page">
        <div className="row auth-header">
          <h1 className="col-12">Sign in</h1>
        </div>
        <div className="row auth-card card-shadow auth-form">
          <div className="col-12">
            <EmailForm onSubmit={this.onSubmit.bind(this)}>
              <React.Fragment>
                <span>Don't have an account? </span>
                <Link to={routes.register.begin} className="link-light-blue">
                  Create Account
                </Link>
              </React.Fragment>
            </EmailForm>
          </div>
        </div>
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
