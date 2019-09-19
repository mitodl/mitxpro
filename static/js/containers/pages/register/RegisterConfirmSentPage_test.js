// @flow
/* global SETTINGS: false */
import { assert } from "chai"

import RegisterConfirmSentPage, {
  RegisterConfirmSentPage as InnerRegisterConfirmSentPage
} from "./RegisterConfirmSentPage"
import IntegrationTestHelper from "../../../util/integration_test_helper"
import { isIf, shouldIf } from "../../../lib/test_utils"

import { routes } from "../../../lib/urls"

describe("RegisterConfirmSentPage", () => {
  const userEmail = "test@example.com"
  const supportEmail = "email@localhost"

  let helper, renderPage

  beforeEach(() => {
    SETTINGS.support_email = supportEmail

    helper = new IntegrationTestHelper()

    renderPage = helper.configureHOCRenderer(
      RegisterConfirmSentPage,
      InnerRegisterConfirmSentPage,
      {},
      {
        location: {
          search: `?email=${encodeURIComponent(userEmail)}`
        }
      }
    )
  })

  afterEach(() => {
    helper.cleanup()
  })

  it("displays a link to email support", async () => {
    const { inner } = await renderPage()
    assert.equal(
      inner.find(".contact-support > a").prop("href"),
      `mailto:${supportEmail}`
    )
  })

  it("displays a link to create account page", async () => {
    const { inner } = await renderPage()
    assert.equal(inner.find("li > a").prop("href"), routes.register.begin)
  })

  it("displays user's email on the page", async () => {
    const { inner } = await renderPage()
    assert.equal(
      inner.find(".confirm-sent-page > p > span").text("href"),
      userEmail
    )
  })

  it("displays a link to course catalog page", async () => {
    const { inner } = await renderPage()
    assert.equal(inner.find(".browse-courses > a").prop("href"), routes.catalog)
  })
})
