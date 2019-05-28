// @flow
import React from "react"
import { compose } from "redux"
import { connect } from "react-redux"
import { connectRequest, mutateAsync, requestAsync } from "redux-query"
import { createStructuredSelector } from "reselect"

import users, { currentUserSelector } from "../../../lib/queries/users"
import { routes } from "../../../lib/urls"
import queries from "../../../lib/queries"
import EditProfileForm from "../../../components/forms/EditProfileForm"

import type { Response } from "redux-query"
import type { Country, CurrentUser, User } from "../../../flow/authTypes"
import type { RouterHistory } from "react-router"

type StateProps = {|
  countries: Array<Country>,
  currentUser: CurrentUser
|}

type DispatchProps = {|
  editProfile: (userProfileData: User) => Promise<Response<User>>,
  getCurrentUser: () => Promise<Response<User>>
|}

type ProfileProps = {|
  history: RouterHistory
|}

type Props = {|
  ...StateProps,
  ...DispatchProps,
  ...ProfileProps
|}

export class EditProfilePage extends React.Component<Props> {
  async onSubmit(profileData: User, { setSubmitting, setErrors }: Object) {
    const { editProfile, history } = this.props

    try {
      const {
        body: { errors }
      }: { body: Object } = await editProfile(profileData)

      if (errors && errors.length > 0) {
        setErrors({
          email: errors[0]
        })
      } else {
        history.push(routes.profile.view)
      }
    } finally {
      setSubmitting(false)
    }
  }

  render() {
    const { countries, currentUser } = this.props
    return (
      <div className="container auth-page registration-page">
        <div className="auth-header row d-flex  align-items-center justify-content-between flex-nowrap">
          <div className="col-auto flex-shrink-1">
            <h1>Edit Profile</h1>
          </div>
        </div>
        <div className="auth-card card-shadow row">
          <div className="container">
            <div className="row">
              <div className="col-12 auth-form">
                {currentUser.is_authenticated ? (
                  <EditProfileForm
                    countries={countries}
                    user={currentUser}
                    onSubmit={this.onSubmit.bind(this)}
                  />
                ) : (
                  <div className="row">
                    You must be logged in to edit your profile.
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    )
  }
}

const editProfile = (userProfileData: User) =>
  mutateAsync(users.editProfileMutation(userProfileData))

const getCurrentUser = () =>
  requestAsync({
    ...users.currentUserQuery(),
    force: true
  })

const mapStateToProps = createStructuredSelector({
  currentUser: currentUserSelector,
  countries:   queries.users.countriesSelector
})

const mapDispatchToProps = {
  editProfile: editProfile,
  getCurrentUser
}

const mapPropsToConfigs = () => [queries.users.countriesQuery()]

export default compose(
  connect(
    mapStateToProps,
    mapDispatchToProps
  ),
  connectRequest(mapPropsToConfigs)
)(EditProfilePage)
