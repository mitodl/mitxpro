// @flow
/* global SETTINGS:false */
import React from "react"
import DocumentTitle from "react-document-title"
import { REGISTER_DENIED_PAGE_TITLE } from "../../../constants"
import { connect } from "react-redux"
import { createStructuredSelector } from "reselect"

import { qsErrorSelector } from "../../../lib/selectors"

type Props = {|
  params: { error: ?string }
|}

export class RegisterDeniedPage extends React.Component<Props> {
  render() {
    const {
      params: { error }
    } = this.props

    return (
      <DocumentTitle
        title={`${SETTINGS.site_name} | ${REGISTER_DENIED_PAGE_TITLE}`}
      >
        <div className="container auth-page">
          <div className="auth-card card-shadow row">
            <div className="col-12">
              <div className="register-error-icon" />
              <p>Sorry, we cannot create an account for you at this time.</p>
              {error ? <p className="error-detail">{error}</p> : null}
              <p>
                Please contact us at{" "}
                <a href={`mailto:${SETTINGS.support_email}`}>
                  {SETTINGS.support_email}
                </a>
              </p>
            </div>
          </div>
        </div>
      </DocumentTitle>
    )
  }
}

const mapStateToProps = createStructuredSelector({
  params: createStructuredSelector({ error: qsErrorSelector })
})

export default connect(mapStateToProps)(RegisterDeniedPage)
