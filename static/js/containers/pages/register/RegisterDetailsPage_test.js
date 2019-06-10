// @flow
import { assert } from "chai"
import sinon from "sinon"

import RegisterDetailsPage, {
  RegisterDetailsPage as InnerRegisterDetailsPage
} from "./RegisterDetailsPage"
import IntegrationTestHelper, {
  createComponentRenderer
} from "../../../util/integration_test_helper"
import {
  STATE_REGISTER_EXTRA_DETAILS,
  STATE_USER_BLOCKED,
  STATE_ERROR,
  STATE_ERROR_TEMPORARY,
  FLOW_REGISTER
} from "../../../lib/auth"
import { routes } from "../../../lib/urls"

describe("RegisterDetailsPage", () => {
  const detailsData = {
    name:          "Sally",
    password:      "password1",
    legal_address: {
      address: "main st"
    }
  }
  const partialToken = "partialTokenTestValue"
  const body = {
    flow:          FLOW_REGISTER,
    partial_token: partialToken,
    ...detailsData
  }
  const renderer = createComponentRenderer(
    RegisterDetailsPage
  ).withConfiguredHistory({
    initialEntries: [`/?partial_token=${partialToken}`]
  })
  const hocRenderer = renderer.withInnerComponent(InnerRegisterDetailsPage)

  let helper, setSubmittingStub, setErrorsStub

  beforeEach(() => {
    helper = new IntegrationTestHelper()

    setSubmittingStub = helper.sandbox.stub()
    setErrorsStub = helper.sandbox.stub()
  })

  afterEach(() => {
    helper.cleanup()
  })

  it.only("displays a form", async () => {
    const { inner } = await hocRenderer.render()

    console.log(inner.html())

    assert.ok(inner.find("RegisterDetailsForm").exists())
  })

  it("handles onSubmit for an error response", async () => {
    const { inner, history } = await hocRenderer.render()
    const error = "error message"

    helper.handleRequestStub.returns({
      body: {
        state:  STATE_ERROR,
        errors: [error]
      }
    })

    const onSubmit = inner.find("RegisterDetailsForm").prop("onSubmit")

    await onSubmit(detailsData, {
      setSubmitting: setSubmittingStub,
      setErrors:     setErrorsStub
    })

    sinon.assert.calledWith(
      helper.handleRequestStub,
      "/api/register/details/",
      "POST",
      { body, headers: undefined, credentials: undefined }
    )

    assert.lengthOf(history, 1)
    sinon.assert.calledWith(setErrorsStub, {
      name: error
    })
    sinon.assert.calledWith(setSubmittingStub, false)
  })

  //
  ;[
    [STATE_ERROR_TEMPORARY, [], routes.register.error, ""],
    [STATE_ERROR, [], routes.register.error, ""], // cover the case with an error but no  messages
    [
      STATE_REGISTER_EXTRA_DETAILS,
      [],
      routes.register.extra,
      "?partial_token=new_partial_token"
    ],
    [
      STATE_USER_BLOCKED,
      ["error_code"],
      routes.register.denied,
      "?error=error_code"
    ],
    [STATE_USER_BLOCKED, [], routes.register.denied, ""]
  ].forEach(([state, errors, pathname, search]) => {
    it("redirects to ${pathname} when it receives auth state ${state}", async () => {
      const { inner, history } = await hocRenderer.render()

      helper.handleRequestStub.returns({
        body: {
          state,
          errors,
          partial_token: "new_partial_token"
        }
      })

      const onSubmit = inner.find("RegisterDetailsForm").prop("onSubmit")

      await onSubmit(detailsData, {
        setSubmitting: setSubmittingStub,
        setErrors:     setErrorsStub
      })

      sinon.assert.calledWith(
        helper.handleRequestStub,
        "/api/register/details/",
        "POST",
        { body, headers: undefined, credentials: undefined }
      )

      assert.lengthOf(history, 2)
      assert.include(history.location, {
        pathname,
        search
      })
      sinon.assert.notCalled(setErrorsStub)
      sinon.assert.calledWith(setSubmittingStub, false)
    })
  })
})
