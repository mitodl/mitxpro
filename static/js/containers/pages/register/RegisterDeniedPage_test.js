// @flow
/* global SETTINGS: false */
import { assert } from "chai"

import RegisterDeniedPage, {
  RegisterDeniedPage as InnerRegisterDeniedPage
} from "./RegisterDeniedPage"
import IntegrationTestHelper from "../../../util/integration_test_helper"

describe("RegisterDeniedPage", () => {
  const error = "errorTestValue"
  const email = "email@localhost"

  let helper, renderPage

  beforeEach(() => {
    SETTINGS.support_email = email

    helper = new IntegrationTestHelper()

    renderPage = helper.configureHOCRenderer(
      RegisterDeniedPage,
      InnerRegisterDeniedPage,
      {},
      {
        location: {
          search: `?error=${error}`
        }
      }
    )
  })

  afterEach(() => {
    helper.cleanup()
  })

  it("displays a link to email support", async () => {
    const { inner } = await renderPage()

    assert.equal(inner.find("a").prop("href"), `mailto:${email}`)
  })

  //
  ;[true, false].forEach(hasError => {
    it(`${hasError ? "does" : "does not"} show an error message if ${
      hasError ? "present in" : "absent from"
    } the query string`, async () => {
      const { inner } = await renderPage()

      const detail = inner.find(".error-detail")
      if (hasError) {
        assert.ok(detail.exists())
        assert.equal(detail.text(), error)
      } else {
        assert.ok(detail.exists())
      }
    })
  })
})
