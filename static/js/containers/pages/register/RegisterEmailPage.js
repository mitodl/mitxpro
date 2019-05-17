// @flow
import React from "react"
import { compose } from "redux"
import { connect } from "react-redux"
import { mutateAsync } from "redux-query"
import { createStructuredSelector } from "reselect"

import queries from "../../../lib/queries"
import { routes } from "../../../lib/urls"
import { STATE_REGISTER_CONFIRM_SENT } from "../../../lib/auth"

import { qsNextSelector } from "../../../lib/selectors"

import RegisterEmailForm from "../../../components/forms/RegisterEmailForm"

import type { RouterHistory, Location } from "react-router"
import type { Response } from "redux-query"
import type { AuthResponse } from "../../../flow/authTypes"

type Props = {
  location: Location,
  history: RouterHistory,
  params: { next: string },
  registerEmail: (
    email: string,
    recaptcha: ?string,
    next: ?string
  ) => Promise<Response<AuthResponse>>
}

class RegisterEmailPage extends React.Component<Props> {
  async onSubmit({ email, recaptcha }, { setSubmitting, setErrors }) {
    const {
      registerEmail,
      params: { next },
      history
    } = this.props

    try {
      const {
        body: { state, errors }
      }: { body: AuthResponse } = await registerEmail(email, recaptcha, next)

      if (state === STATE_REGISTER_CONFIRM_SENT) {
        history.push(routes.dashboard)
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
        <RegisterEmailForm onSubmit={this.onSubmit.bind(this)} />
      </div>
    )
  }
}

const mapStateToProps = createStructuredSelector({
  params: createStructuredSelector({
    next: qsNextSelector
  })
})

const registerEmail = (email: string, recaptcha: ?string, nextUrl: ?string) =>
  mutateAsync(queries.auth.registerEmailMutation(email, recaptcha, nextUrl))

const mapDispatchToProps = {
  registerEmail
}

export default compose(
  connect(
    mapStateToProps,
    mapDispatchToProps
  )
)(RegisterEmailPage)
