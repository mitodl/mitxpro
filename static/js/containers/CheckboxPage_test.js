// @flow
import { assert } from "chai"
import IntegrationTestHelper from "../util/integration_test_helper"

describe("CheckboxPage", () => {
  let helper, renderComponent

  beforeEach(() => {
    helper = new IntegrationTestHelper()
    renderComponent = helper.renderComponent.bind(helper)
  })

  afterEach(() => {
    helper.cleanup()
  })

  it("renders properly", () => {
    return renderComponent("/").then(([wrapper]) => {
      assert.include(wrapper.text(), "Click the checkbox:")
    })
  })
})
