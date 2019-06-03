// @flow
/* global SETTINGS: false */
import { assert } from "chai"

import RegisterDeniedPage, {
  RegisterDeniedPage as InnerRegisterDeniedPage
} from "./RegisterDeniedPage"
import IntegrationTestHelper from "../../../util/integration_test_helper"
import { isIf, shouldIf } from "../../../lib/test_utils"

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
          search: ""
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
    it(`${shouldIf(hasError)} show an error message if ${isIf(
      hasError
    )} in the query string`, async () => {
      const { inner } = await renderPage(
        {},
        hasError
          ? {
            location: {
              search: `?error=${error}`
            }
          }
          : {}
      )

      const detail = inner.find(".error-detail")

      assert.equal(detail.exists(), hasError)
      if (hasError) {
        assert.equal(detail.text(), error)
      }
    })
  })
})
