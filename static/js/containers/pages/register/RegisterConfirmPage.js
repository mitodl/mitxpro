// @flow
import React from "react"
import { compose } from "redux"
import { connect } from "react-redux"
import { mutateAsync, connectRequest } from "redux-query"
import qs from "query-string"
import { path } from "ramda"
import { createStructuredSelector } from "reselect"

import queries from "../../../lib/queries"
import { routes } from "../../../lib/urls"
import { STATE_REGISTER_DETAILS } from "../../../lib/auth"

import { authSelector } from "../../../lib/queries/auth"
import {
  qsVerificationCodeSelector,
  qsPartialTokenSelector
} from "../../../lib/selectors"

import type { RouterHistory, Location } from "react-router"
import type { AuthResponse } from "../../../flow/authTypes"

type Props = {
  location: Location,
  history: RouterHistory,
  auth: ?AuthResponse
}

class RegisterProfilePage extends React.Component<Props> {
  componentDidUpdate(prevProps) {
    const { auth, history } = this.props
    const prevState = path(["auth", "state"], prevProps)

    if (
      auth &&
      auth.partialToken &&
      auth.state !== prevState &&
      auth.state === STATE_REGISTER_DETAILS
    ) {
      const params = qs.stringify({
        partial_token: auth.partialToken
      })
      history.push(`${routes.register.profile}?${params}`)
    }
  }

  render() {
    return (
      <div>
        <p>Confirming...</p>
      </div>
    )
  }
}

const mapStateToProps = createStructuredSelector({
  auth:   authSelector,
  params: createStructuredSelector({
    verificationCode: qsVerificationCodeSelector,
    partialToken:     qsPartialTokenSelector
  })
})

const registerConfirmEmail = (code: string, partialToken: string) =>
  mutateAsync(queries.auth.registerConfirmEmailMutation(code, partialToken))

const mapPropsToConfig = ({ params: { verificationCode, partialToken } }) =>
  registerConfirmEmail(verificationCode, partialToken)

export default compose(
  connect(mapStateToProps),
  connectRequest(mapPropsToConfig)
)(RegisterProfilePage)
