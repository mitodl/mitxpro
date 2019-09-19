// @flow
/* global SETTINGS: false */
import React from "react"
import DocumentTitle from "react-document-title"
import { connect } from "react-redux"
import { createStructuredSelector } from "reselect"

import { REGISTER_CONFIRM_PAGE_TITLE } from "../../../constants"
import { routes } from "../../../lib/urls"
import { qsEmailSelector } from "../../../lib/selectors"

type Props = {|
  params: { email: ?string }
|}

export class RegisterConfirmSentPage extends React.Component<Props> {
  render() {
    const {
      params: { email }
    } = this.props

    return (
      <DocumentTitle
        title={`${SETTINGS.site_name} | ${REGISTER_CONFIRM_PAGE_TITLE}`}
      >
        <div className="container auth-page">
          <h1>Sign Up</h1>

          <div className="confirm-sent-page">
            <h2 className="text-center font-weight-600">Thank You!</h2>
            <p>
              We sent an email to <span className="email">{email}</span>
              ,<br /> please verify your address to continue.
            </p>
            <p>
              <b>
                If you do NOT receive your verification email, here’s what to
                do:
              </b>
            </p>
            <ol>
              <li>
                <span className="font-weight-600">Wait a few moments.</span> It
                might take several minutes to receive your verification email.
              </li>
              <li>
                <span className="font-weight-600">Check your spam folder.</span>{" "}
                It might be there.
              </li>
              <li>
                <span className="font-weight-600">Is your email correct?</span>{" "}
                If you made a typo, no problem, just try{" "}
                <a href={routes.register.begin}>creating an account</a> again.
              </li>
            </ol>
            <div className="contact-support">
              <span className="font-weight-600">
                Still no verification email?
              </span>{" "}
              Please contact our
              <a href={`mailto:${SETTINGS.support_email}`}>
                {` ${SETTINGS.site_name} Customer Support Center`}.
              </a>
            </div>
            <div className="browse-courses text-right">
              <a href={routes.catalog}>Browse courses</a>
            </div>
          </div>
        </div>
      </DocumentTitle>
    )
  }
}

const mapStateToProps = createStructuredSelector({
  params: createStructuredSelector({ email: qsEmailSelector })
})

export default connect(mapStateToProps)(RegisterConfirmSentPage)
