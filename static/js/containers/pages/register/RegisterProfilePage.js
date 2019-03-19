// @flow
import React from "react"
import { compose } from "redux"
import { connect } from "react-redux"
import { mutateAsync } from "redux-query"
import { createStructuredSelector } from "reselect"

import queries from "../../../lib/queries"
import { routes } from "../../../lib/urls"
import { STATE_SUCCESS } from "../../../lib/auth"

import { qsPartialTokenSelector } from "../../../lib/selectors"

import { RegisterProfileForm } from "../../../components/forms/register"

import type { RouterHistory, Location } from "react-router"
import type { Response } from "redux-query"
import type { AuthResponse } from "../../../flow/authTypes"

type Props = {
  location: Location,
  history: RouterHistory,
  params: { partialToken: string },
  registerDetails: (
    name: string,
    password: string,
    partialToken: string
  ) => Promise<Response<AuthResponse>>
}

class RegisterProfilePage extends React.Component<Props> {
  async onSubmit({ name, password }, { setSubmitting, setErrors }) {
    const {
      registerDetails,
      params: { partialToken },
      history
    } = this.props

    /* eslint-disable camelcase */
    try {
      const {
        body: { state, errors }
      }: { body: AuthResponse } = await registerDetails(
        name,
        password,
        partialToken
      )

      if (state === STATE_SUCCESS) {
        history.push(routes.home)
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
        <RegisterProfileForm onSubmit={this.onSubmit.bind(this)} />
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
) =>
  mutateAsync(
    queries.auth.registerDetailsMutation(name, password, partialToken)
  )

const mapDispatchToProps = {
  registerDetails
}

export default compose(
  connect(
    mapStateToProps,
    mapDispatchToProps
  )
)(RegisterProfilePage)
