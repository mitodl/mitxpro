// @flow
import React from "react"
import { compose } from "redux"
import { connect } from "react-redux"
import { mutateAsync } from "redux-query"

import { addUserNotification } from "../../../actions"
import auth from "../../../lib/queries/auth"
import { routes } from "../../../lib/urls"

import ChangePasswordForm from "../../../components/forms/ChangePasswordForm"

import type { Match, RouterHistory } from "react-router"
import type { ChangePasswordFormValues } from "../../../components/forms/ChangePasswordForm"

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
    { newPassword, confirmPassword }: ChangePasswordFormValues,
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

      if (response.status === 200) {
        addUserNotification(
          "Your password has been updated, you may use it to login now."
        )
        history.push(routes.login.begin)
      } else {
        addUserNotification(
          "Unable to reset your password with that link, please try again."
        )
        history.push(routes.login.forgot.begin)
      }
    } finally {
      setSubmitting(false)
    }
  }

  render() {
    return (
      <div className="container auth-page">
        <div className="row auth-header">
          <h1 className="col-12">Forgot Password</h1>
        </div>
        <div className="row auth-card card-shadow auth-form">
          <div className="col-12">
            <p>Enter a new password for your account.</p>
          </div>
          <div className="col-12">
            <ChangePasswordForm onSubmit={this.onSubmit.bind(this)} />
          </div>
        </div>
      </div>
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
