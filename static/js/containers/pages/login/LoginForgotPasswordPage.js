// @flow
/* global SETTINGS: false */
import React from "react"
import DocumentTitle from "react-document-title"
import { FORGOT_PASSWORD_PAGE_TITLE } from "../../../constants"
import { compose } from "redux"
import { connect } from "react-redux"
import { mutateAsync } from "redux-query"
import { Link } from "react-router-dom"

import { addUserNotification } from "../../../actions"
import auth from "../../../lib/queries/auth"
import { routes } from "../../../lib/urls"
import { ALERT_TYPE_TEXT } from "../../../constants"

import EmailForm from "../../../components/forms/EmailForm"

import type { RouterHistory } from "react-router"
import type { EmailFormValues } from "../../../components/forms/EmailForm"

type Props = {
  history: RouterHistory,
  forgotPassword: (email: string) => Promise<any>
}

type State = {
  forgotEmailSent: boolean,
  text: Object | null
}

const passwordResetText = (email: string) => (
  <p>
    If an account with the email <span className="email">{email}</span> <br />{" "}
    exists, an email has been sent with a password reset link.
  </p>
)

export class LoginForgotPasswordPage extends React.Component<Props, State> {
  constructor(props: Props, state: State) {
    super(props, state)
    this.state = { forgotEmailSent: false, text: null }
  }
  async onSubmit({ email }: EmailFormValues, { setSubmitting }: any) {
    const { forgotPassword, history } = this.props

    try {
      await forgotPassword(email)
      this.setState((state, props) => {
        return {
          forgotEmailSent: true,
          text:            passwordResetText(email)
        }
      })

      history.push(routes.login.forgot)
    } finally {
      setSubmitting(false)
    }
  }

  resetEmailLinkSent() {
    this.setState({
      forgotEmailSent: false,
      text:            null
    })
  }

  render() {
    return (
      <DocumentTitle
        title={`${SETTINGS.site_name} | ${FORGOT_PASSWORD_PAGE_TITLE}`}
      >
        <div className="container auth-page">
          <div className="auth-header">
            <h1>Forgot Password</h1>
          </div>
          {this.state.forgotEmailSent ? (
            <div className="card-shadow confirm-sent-page">
              <h3 className="text-center">Thank You!</h3>
              {this.state.text}
              <p>
                <b>
                  If you do NOT receive your password reset email, here's what
                  to do:
                </b>
              </p>
              <ol>
                <li>
                  <b>Wait a few moments.</b> It might take several minutes to
                  receive your password reset email.
                </li>
                <li>
                  <b>Check your spam folder.</b> It might be there.
                </li>
                <li>
                  <b>Is your email correct?</b> If you made a typo, no problem,
                  just try to
                  <Link
                    to={routes.login.forgot.begin}
                    onClick={this.resetEmailLinkSent.bind(this)}
                  >
                    {` reset your password `}
                  </Link>
                  again.
                </li>
              </ol>
              <div className="contact-support">
                <b>Still no password reset email? </b>
                Please contact our {` ${SETTINGS.site_name} `}
                <a href={`mailto:${SETTINGS.support_email}`}>
                  Customer Support Center.
                </a>
              </div>
            </div>
          ) : (
            <div className="auth-card card-shadow auth-form">
              <p>Enter your email to receive a password reset link.</p>
              <EmailForm onSubmit={this.onSubmit.bind(this)} />
            </div>
          )}
        </div>
      </DocumentTitle>
    )
  }
}

const forgotPassword = (email: string) =>
  mutateAsync(auth.forgotPasswordMutation(email))

const mapDispatchToProps = {
  forgotPassword,
  addUserNotification
}

export default compose(
  connect(
    null,
    mapDispatchToProps
  )
)(LoginForgotPasswordPage)
