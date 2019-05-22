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
import type { Country, User } from "../../../flow/authTypes"
import type { RouterHistory } from "react-router"

type StateProps = {|
  countries: Array<Country>,
  currentUser: User
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

class EditProfilePage extends React.Component<Props> {
  async onSubmit(profileData, { setSubmitting, setErrors }) {
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
      <div className="registration-form">
        <div className="form-group row">
          <h3 className="col-8">Edit Profile</h3>
        </div>
        <div className="inner-form">
          <EditProfileForm
            countries={countries}
            user={currentUser}
            onSubmit={this.onSubmit.bind(this)}
          />
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
