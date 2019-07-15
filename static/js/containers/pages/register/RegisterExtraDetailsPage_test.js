// @flow
import { assert } from "chai"
import sinon from "sinon"

import RegisterExtraDetailsPage, {
  RegisterExtraDetailsPage as InnerRegisterExtraDetailsPage
} from "./RegisterExtraDetailsPage"
import IntegrationTestHelper from "../../../util/integration_test_helper"
import {
  STATE_SUCCESS,
  STATE_USER_BLOCKED,
  STATE_ERROR,
  STATE_ERROR_TEMPORARY,
  STATE_REGISTER_EXTRA_DETAILS
} from "../../../lib/auth"
import { routes } from "../../../lib/urls"
import { makeRegisterAuthResponse } from "../../../factories/auth"

describe("RegisterExtraDetailsPage", () => {
  const profileData = {
    profile: {
      gender:     "N/A",
      birth_year: "2000",
      company:    "Employer",
      job_title:  "Employee"
    }
  }

  let helper,
    renderPage,
    setSubmittingStub,
    setErrorsStub,
    body,
    authResponse,
    partialToken

  beforeEach(() => {
    helper = new IntegrationTestHelper()
    authResponse = makeRegisterAuthResponse({
      state: STATE_REGISTER_EXTRA_DETAILS
    })

    partialToken = authResponse.partial_token

    body = {
      flow:          authResponse.flow,
      partial_token: partialToken,
      ...profileData.profile
    }

    setSubmittingStub = helper.sandbox.stub()
    setErrorsStub = helper.sandbox.stub()

    renderPage = helper.configureHOCRenderer(
      RegisterExtraDetailsPage,
      InnerRegisterExtraDetailsPage,
      {},
      {
        location: {
          // $FlowFixMe: partialToken is not undefined
          search: `?partial_token=${partialToken}`
        }
      }
    )
  })

  afterEach(() => {
    helper.cleanup()
  })

  it("displays a form", async () => {
    const { inner } = await renderPage()

    assert.ok(inner.find("RegisterExtraDetailsForm").exists())
  })

  it("handles onSubmit for an error response", async () => {
    const { inner } = await renderPage()
    const error = "error message"
    const fieldErrors = {
      name: error
    }

    helper.handleRequestStub.returns({
      body: makeRegisterAuthResponse({
        state:        STATE_ERROR,
        field_errors: fieldErrors
      })
    })

    const onSubmit = inner.find("RegisterExtraDetailsForm").prop("onSubmit")

    await onSubmit(profileData, {
      setSubmitting: setSubmittingStub,
      setErrors:     setErrorsStub
    })

    sinon.assert.calledWith(
      helper.handleRequestStub,
      "/api/register/extra/",
      "POST",
      { body, headers: undefined, credentials: undefined }
    )

    assert.lengthOf(helper.browserHistory, 1)
    sinon.assert.calledWith(setErrorsStub, fieldErrors)
    sinon.assert.calledWith(setSubmittingStub, false)
  })

  it(`redirects to /dashboard when it receives auth state ${STATE_SUCCESS}`, async () => {
    const { inner } = await renderPage()

    helper.handleRequestStub.returns({
      body: makeRegisterAuthResponse({
        state:         STATE_SUCCESS,
        partial_token: undefined
      })
    })

    const onSubmit = inner.find("RegisterExtraDetailsForm").prop("onSubmit")

    await onSubmit(profileData, {
      setSubmitting: setSubmittingStub,
      setErrors:     setErrorsStub
    })

    sinon.assert.calledWith(
      helper.handleRequestStub,
      "/api/register/extra/",
      "POST",
      { body, headers: undefined, credentials: undefined }
    )
    assert.equal(window.location.href, `http://fake${routes.dashboard}`)

    sinon.assert.notCalled(setErrorsStub)
    sinon.assert.calledWith(setSubmittingStub, false)
  })

  //
  ;[
    [STATE_ERROR_TEMPORARY, [], routes.register.error, ""],
    [STATE_ERROR, [], routes.register.error, ""], // cover the case with an error but no  messages
    [
      STATE_USER_BLOCKED,
      ["error_code"],
      routes.register.denied,
      "?error=error_code"
    ],
    [STATE_USER_BLOCKED, [], routes.register.denied, ""]
  ].forEach(([state, errors, pathname, search]) => {
    it(`redirects to ${pathname} when it receives auth state ${state}`, async () => {
      const { inner } = await renderPage()

      helper.handleRequestStub.returns({
        body: makeRegisterAuthResponse({
          state,
          errors,
          partial_token: undefined
        })
      })

      const onSubmit = inner.find("RegisterExtraDetailsForm").prop("onSubmit")

      await onSubmit(profileData, {
        setSubmitting: setSubmittingStub,
        setErrors:     setErrorsStub
      })

      sinon.assert.calledWith(
        helper.handleRequestStub,
        "/api/register/extra/",
        "POST",
        { body, headers: undefined, credentials: undefined }
      )

      assert.include(helper.browserHistory.location, {
        pathname,
        search
      })
      if (state === STATE_ERROR) {
        sinon.assert.calledWith(setErrorsStub, {})
      } else {
        sinon.assert.notCalled(setErrorsStub)
      }
      sinon.assert.calledWith(setSubmittingStub, false)
    })
  })
})
