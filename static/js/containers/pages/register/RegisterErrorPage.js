// @flow
/* global SETTINGS:false */
import React from "react"
import DocumentTitle from "react-document-title"
import { REGISTER_ERROR_PAGE_TITLE } from "../../../constants"

const RegisterErrorPage = () => (
  <DocumentTitle title={`${SETTINGS.site_name} | ${REGISTER_ERROR_PAGE_TITLE}`}>
    <div className="container auth-page">
      <div className="auth-card card-shadow row">
        <div className="col-12">
          <div className="register-error-icon" />
          <p>Sorry, we cannot create an account for you at this time.</p>
          <p>
            Please try again later or contact us at{" "}
            <a href={`mailto:${SETTINGS.support_email}`}>
              {SETTINGS.support_email}
            </a>
          </p>
        </div>
      </div>
    </div>
  </DocumentTitle>
)

export default RegisterErrorPage
