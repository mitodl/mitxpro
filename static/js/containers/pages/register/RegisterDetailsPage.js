// @flow
import React from "react"
import { compose } from "redux"
import { connect } from "react-redux"
import { mutateAsync, requestAsync } from "redux-query"
import { createStructuredSelector } from "reselect"

import auth from "../../../lib/queries/auth"
import users from "../../../lib/queries/users"
import { routes } from "../../../lib/urls"
import { STATE_SUCCESS } from "../../../lib/auth"

import { qsPartialTokenSelector } from "../../../lib/selectors"

import RegisterDetailsForm from "../../../components/forms/RegisterDetailsForm"

import type { RouterHistory, Location } from "react-router"
import type { Response } from "redux-query"
import type { AuthResponse, User } from "../../../flow/authTypes"

type Props = {
  location: Location,
  history: RouterHistory,
  params: { partialToken: string },
  registerDetails: (
    name: string,
    password: string,
    partialToken: string
  ) => Promise<Response<AuthResponse>>,
  getCurrentUser: () => Promise<Response<User>>
}

class RegisterProfilePage extends React.Component<Props> {
  async onSubmit({ name, password }, { setSubmitting, setErrors }) {
    const {
      registerDetails,
      // getCurrentUser,
      params: { partialToken }
      // history
    } = this.props

    try {
      const {
        body: { state, errors }
      }: { body: AuthResponse } = await registerDetails(
        name,
        password,
        partialToken
      )

      if (state === STATE_SUCCESS) {
        // await getCurrentUser()
        // history.push(routes.home)
        window.location.href = routes.root
      } else if (errors.length > 0) {
        setErrors({
          email: errors[0]
        })
      }
    } finally {
      setSubmitting(false)
    }
  }

  render() {
    return (
      <div>
        <RegisterDetailsForm onSubmit={this.onSubmit.bind(this)} />
      </div>
    )
  }
}

const mapStateToProps = createStructuredSelector({
  params: createStructuredSelector({ partialToken: qsPartialTokenSelector })
})

const registerDetails = (
  name: string,
  password: string,
  partialToken: string
) => mutateAsync(auth.registerDetailsMutation(name, password, partialToken))

const getCurrentUser = () =>
  requestAsync({
    ...users.currentUserQuery(),
    force: true
  })

const mapDispatchToProps = {
  registerDetails,
  getCurrentUser
}

export default compose(
  connect(
    mapStateToProps,
    mapDispatchToProps
  )
)(RegisterProfilePage)
