// @flow
/* global SETTINGS: false */
import React from "react"
import DocumentTitle from "react-document-title"
import { REGISTER_CONFIRM_PAGE_TITLE } from "../../../constants"
import { compose } from "redux"
import { connect } from "react-redux"
import { Link } from "react-router-dom"
import { mutateAsync, connectRequest } from "redux-query"
import { path } from "ramda"
import { createStructuredSelector } from "reselect"

import { addUserNotification } from "../../../actions"
import { ALERT_TYPE_TEXT } from "../../../constants"
import queries from "../../../lib/queries"
import { routes } from "../../../lib/urls"
import {
  STATE_REGISTER_DETAILS,
  STATE_INVALID_EMAIL,
  handleAuthResponse,
  INFORMATIVE_STATES,
  STATE_INVALID_LINK,
  STATE_EXISTING_ACCOUNT
} from "../../../lib/auth"

import { authSelector } from "../../../lib/queries/auth"
import {
  qsVerificationCodeSelector,
  qsPartialTokenSelector,
  qsSelector
} from "../../../lib/selectors"

import type { RouterHistory, Location } from "react-router"
import type { AuthResponse } from "../../../flow/authTypes"

type Props = {
  addUserNotification: Function,
  location: Location,
  history: RouterHistory,
  auth: ?AuthResponse
}

export class RegisterConfirmPage extends React.Component<Props> {
  componentDidUpdate(prevProps: Props) {
    const { addUserNotification, auth, history } = this.props
    const prevState = path(["auth", "state"], prevProps)

    if (auth && auth.state !== prevState) {
      handleAuthResponse(history, auth, {
        [STATE_REGISTER_DETAILS]: () => {
          addUserNotification({
            "email-verified": {
              type:  ALERT_TYPE_TEXT,
              props: {
                text:
                  "Success! We've verified your email. Please finish your account creation below."
              }
            }
          })
        }
      })
    }
  }

  render() {
    const { auth } = this.props

    return (
      <DocumentTitle
        title={`${SETTINGS.site_name} | ${REGISTER_CONFIRM_PAGE_TITLE}`}
      >
        <div className="container auth-page">
          <div className="row">
            <div className="col">
              {auth && INFORMATIVE_STATES.indexOf(auth.state) > -1 ? (
                this.getAppropriateInformationFragment(auth.state)
              ) : (
                <p>Confirming...</p>
              )}
            </div>
          </div>
        </div>
      </DocumentTitle>
    )
  }

  getAppropriateInformationFragment(state: string) {
    let preLinkText = ""
    let postLinkText = ""
    let linkRoute = null
    if (state === STATE_INVALID_LINK) {
      preLinkText = "This invitation is invalid or has expired. Please"
      postLinkText = "to register again"
      linkRoute = routes.register.begin
    } else if (state === STATE_EXISTING_ACCOUNT) {
      preLinkText = "You already have an xPRO account. Please"
      postLinkText = "to sign in"
      linkRoute = routes.login.begin
    } else if (state === STATE_INVALID_EMAIL) {
      preLinkText = "No confirmation code was provided or it has expired."
      postLinkText = "to register again"
      linkRoute = routes.register.begin
    }
    return (
      <React.Fragment>
        <span className={"confirmation-message"}>
          {preLinkText}{" "}
          <Link class={"action-link"} to={linkRoute}>
            click here {postLinkText}
          </Link>
          .
        </span>
      </React.Fragment>
    )
  }
}

const mapStateToProps = createStructuredSelector({
  auth:     authSelector,
  qsParams: qsSelector
})

const mapPropsToConfig = ({ qsParams }) =>
  mutateAsync(queries.auth.registerConfirmEmailMutation(qsParams))

const mapDispatchToProps = {
  addUserNotification
}

export default compose(
  connect(
    mapStateToProps,
    mapDispatchToProps
  ),
  connectRequest(mapPropsToConfig)
)(RegisterConfirmPage)
