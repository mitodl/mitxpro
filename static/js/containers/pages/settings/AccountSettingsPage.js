// @flow
/* global SETTINGS: false */
import React from "react"
import DocumentTitle from "react-document-title"
import { ACCOUNT_SETTINGS_PAGE_TITLE } from "../../../constants"
import { compose } from "redux"
import { connect } from "react-redux"
import { mutateAsync } from "redux-query"

import { addUserNotification } from "../../../actions"
import auth from "../../../lib/queries/auth"
import { routes } from "../../../lib/urls"
import { ALERT_TYPE_TEXT } from "../../../constants"

import ChangePasswordForm from "../../../components/forms/ChangePasswordForm"
import ChangeEmailForm from "../../../components/forms/ChangeEmailForm"

import type { User } from "../../../flow/authTypes"

import { createStructuredSelector } from "reselect"
import { currentUserSelector } from "../../../lib/queries/users"

import type { RouterHistory } from "react-router"
import type { ChangePasswordFormValues } from "../../../components/forms/ChangePasswordForm"
import type { ChangeEmailFormValues } from "../../../components/forms/ChangeEmailForm"
import type { Response } from "redux-query"

type Props = {
  history: RouterHistory,
  changePassword: (
    oldPassword: string,
    newPassword: string,
    confirmPassword: string
  ) => Promise<any>,
  changeEmail: (newEmail: string, password: string) => Promise<any>,
  addUserNotification: Function,
  currentUser: User
}

export class AccountSettingsPage extends React.Component<Props> {
  async onSubmitPasswordForm(
    { oldPassword, newPassword, confirmPassword }: ChangePasswordFormValues,
    { setSubmitting, resetForm }: any
  ) {
    const { addUserNotification, changePassword, history } = this.props

    try {
      const response = await changePassword(
        oldPassword,
        newPassword,
        confirmPassword
      )

      let alertText, color
      if (response.status === 200) {
        alertText = "Your password has been updated successfully."
        color = "success"
      } else {
        alertText = "Unable to reset your password, please try again later."
        color = "danger"
      }

      addUserNotification({
        "password-change": {
          type:  ALERT_TYPE_TEXT,
          color: color,
          props: {
            text: alertText
          }
        }
      })

      history.push(routes.accountSettings)
    } finally {
      resetForm()
      setSubmitting(false)
    }
  }

  async onSubmitEmailForm(
    { email, confirmPassword }: ChangeEmailFormValues,
    { setSubmitting, resetForm }: any
  ) {
    const { addUserNotification, changeEmail, history } = this.props

    try {
      const response = await changeEmail(email, confirmPassword)

      let alertText, color
      if (response.status === 200 || response.status === 201) {
        alertText =
          "You have been sent a verification email on your updated address. Please click on the link in the email to finish email address update."
        color = "success"
      } else {
        alertText =
          "Unable to update your email address, please try again later."
        color = "danger"
      }

      addUserNotification({
        "email-change": {
          type:  ALERT_TYPE_TEXT,
          color: color,
          props: {
            text: alertText
          }
        }
      })

      history.push(routes.accountSettings)
    } finally {
      resetForm()
      setSubmitting(false)
    }
  }

  render() {
    const { currentUser } = this.props

    return (
      <DocumentTitle
        title={`${SETTINGS.site_name} | ${ACCOUNT_SETTINGS_PAGE_TITLE}`}
      >
        <div className="container auth-page account-settings-page">
          <div className="auth-header">
            <h1>User Settings</h1>
          </div>

          <div className="auth-card card-shadow auth-form">
            <h3>Basic Account Information</h3>
            <ChangeEmailForm
              user={currentUser}
              onSubmit={this.onSubmitEmailForm.bind(this)}
            />
            <ChangePasswordForm
              onSubmit={this.onSubmitPasswordForm.bind(this)}
            />
          </div>
        </div>
      </DocumentTitle>
    )
  }
}

const changePassword = (oldPassword: string, newPassword: string) =>
  mutateAsync(auth.changePasswordMutation(oldPassword, newPassword))

const changeEmail = (newEmail: string, password: string) =>
  mutateAsync(auth.changeEmailMutation(newEmail, password))

const mapStateToProps = createStructuredSelector({
  currentUser: currentUserSelector
})

const mapDispatchToProps = {
  changePassword,
  changeEmail,
  addUserNotification
}

export default compose(
  connect(
    mapStateToProps,
    mapDispatchToProps
  )
)(AccountSettingsPage)
