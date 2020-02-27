// @flow
/* global SETTINGS: false */
import React from "react"
import DocumentTitle from "react-document-title"
import { ACCOUNT_SETTINGS_PAGE_TITLE } from "../../../constants"
import { compose } from "redux"
import { connect } from "react-redux"
import { mutateAsync, requestAsync } from "redux-query"
import { Link } from "react-router-dom"

import { addUserNotification } from "../../../actions"
import auth from "../../../lib/queries/auth"
import { routes } from "../../../lib/urls"
import { ALERT_TYPE_TEXT } from "../../../constants"

import ChangePasswordForm from "../../../components/forms/ChangePasswordForm"

import type { User } from "../../../flow/authTypes"

import { createStructuredSelector } from "reselect"
import { currentUserSelector } from "../../../lib/queries/users"

import type { RouterHistory } from "react-router"
import type { ChangePasswordFormValues } from "../../../components/forms/ChangePasswordForm"
import type { Response } from "redux-query"
import users from "../../../lib/queries/users"

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
  async onSubmit(
    {
      oldPassword,
      newPassword,
      confirmPassword,
      email,
      emailPassword
    }: ChangePasswordFormValues,
    { setSubmitting, resetForm }: any
  ) {
    const {
      addUserNotification,
      changePassword,
      changeEmail,
      currentUser,
      history
    } = this.props

    try {
      let alertText, color, alertKey
      if (currentUser && email !== currentUser.email) {
        alertKey = "email-change"
        const response = await changeEmail(email, emailPassword)
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
          [alertKey]: {
            type:  ALERT_TYPE_TEXT,
            color: color,
            props: {
              text: alertText
            }
          }
        })
      }

      if (oldPassword && newPassword && confirmPassword) {
        alertKey = "password-change"
        const response = await changePassword(
          oldPassword,
          newPassword,
          confirmPassword
        )

        if (response.status === 200) {
          alertText = "Your password has been updated successfully."
          color = "success"
        } else {
          alertText = "Unable to reset your password, please try again later."
          color = "danger"
        }
        addUserNotification({
          [alertKey]: {
            type:  ALERT_TYPE_TEXT,
            color: color,
            props: {
              text: alertText
            }
          }
        })
      }
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
            <ChangePasswordForm
              user={currentUser}
              onSubmit={this.onSubmit.bind(this)}
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
