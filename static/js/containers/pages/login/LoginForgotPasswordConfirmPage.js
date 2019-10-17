// @flow
/* global SETTINGS: false */
import React from "react"
import DocumentTitle from "react-document-title"
import { FORGOT_PASSWORD_CONFIRM_PAGE_TITLE } from "../../../constants"
import { compose } from "redux"
import { connect } from "react-redux"
import { mutateAsync } from "redux-query"

import { addUserNotification } from "../../../actions"
import auth from "../../../lib/queries/auth"
import { routes } from "../../../lib/urls"
import { ALERT_TYPE_TEXT } from "../../../constants"

import ResetPasswordForm from "../../../components/forms/ResetPasswordForm"

import type { Match, RouterHistory } from "react-router"
import type { ResetPasswordFormValues } from "../../../components/forms/ResetPasswordForm"

type Props = {
  match: Match,
  history: RouterHistory,
  forgotPasswordConfirm: (
    newPassword: string,
    reNewPassword: string,
    token: string,
    uid: string
  ) => Promise<any>,
  addUserNotification: Function
}

export class LoginForgotPasswordConfirmPage extends React.Component<Props> {
  async onSubmit(
    { newPassword, confirmPassword }: ResetPasswordFormValues,
    { setSubmitting }: any
  ) {
    const {
      addUserNotification,
      forgotPasswordConfirm,
      history,
      match
    } = this.props
    const { token, uid } = match.params

    if (!token || !uid) {
      // this is here to satisfy flow
      return
    }

    try {
      const response = await forgotPasswordConfirm(
        newPassword,
        confirmPassword,
        token,
        uid
      )

      let alertText, redirectRoute
      if (response.status === 200) {
        alertText =
          "Your password has been updated, you may use it to sign in now."
        redirectRoute = routes.login.begin
      } else {
        alertText =
          "Unable to reset your password with that link, please try again."
        redirectRoute = routes.login.forgot.begin
      }

      addUserNotification({
        "forgot-password-confirm": {
          type:  ALERT_TYPE_TEXT,
          props: {
            text: alertText
          }
        }
      })
      history.push(redirectRoute)
    } finally {
      setSubmitting(false)
    }
  }

  render() {
    return (
      <DocumentTitle
        title={`${SETTINGS.site_name} | ${FORGOT_PASSWORD_CONFIRM_PAGE_TITLE}`}
      >
        <div className="container auth-page">
          <div className="row auth-header">
            <h1 className="col-12">Forgot Password</h1>
          </div>
          <div className="row auth-card card-shadow auth-form">
            <div className="col-12">
              <p>Enter a new password for your account.</p>
            </div>
            <div className="col-12">
              <ResetPasswordForm onSubmit={this.onSubmit.bind(this)} />
            </div>
          </div>
        </div>
      </DocumentTitle>
    )
  }
}

const forgotPasswordConfirm = (
  newPassword: string,
  reNewPassword: string,
  token: string,
  uid: string
) =>
  mutateAsync(
    auth.forgotPasswordConfirmMutation(newPassword, reNewPassword, token, uid)
  )

const mapDispatchToProps = {
  forgotPasswordConfirm,
  addUserNotification
}

export default compose(
  connect(
    null,
    mapDispatchToProps
  )
)(LoginForgotPasswordConfirmPage)
