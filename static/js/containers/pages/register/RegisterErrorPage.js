// @flow
/* global SETTINGS:false */
import React from "react"

const RegisterErrorPage = () => (
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
)

export default RegisterErrorPage
