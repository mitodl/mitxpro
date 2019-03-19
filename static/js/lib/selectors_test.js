// @flow
import { assert } from "chai"

import {
  qsPartialTokenSelector,
  qsNextSelector,
  qsVerificationCodeSelector
} from "./selectors"

describe("selector utils", () => {
  const makeSearchProps = search => ({
    location: {
      search
    }
  })

  describe("qsPartialTokenSelector", () => {
    it("should return the partial_token param", () => {
      assert.equal(
        qsPartialTokenSelector(
          {},
          makeSearchProps("abc=123&partial_token=tokenvalue")
        ),
        "tokenvalue"
      )
    })

    it("should return undefined if no partial_token param", () => {
      assert.isUndefined(qsPartialTokenSelector({}, makeSearchProps("abc=123")))
      assert.isUndefined(qsPartialTokenSelector({}, makeSearchProps("")))
    })
  })

  describe("qsVerificationCodeSelector", () => {
    it("should return the verification_code param", () => {
      assert.equal(
        qsVerificationCodeSelector(
          {},
          makeSearchProps("abc=123&verification_code=codevalue")
        ),
        "codevalue"
      )
    })

    it("should return undefined if no verification_code param", () => {
      assert.isUndefined(
        qsVerificationCodeSelector({}, makeSearchProps("abc=123"))
      )
      assert.isUndefined(qsVerificationCodeSelector({}, makeSearchProps("")))
    })
  })

  describe("qsNextSelector", () => {
    it("should return the next param", () => {
      const url = "/url/for/next"
      assert.equal(
        qsNextSelector(
          {},
          makeSearchProps(`abc=123&next=${encodeURIComponent(url)}`)
        ),
        url
      )
    })

    it("should return '/' if no next param", () => {
      assert.equal(qsNextSelector({}, makeSearchProps("abc=123")), "/")
      assert.equal(qsNextSelector({}, makeSearchProps("")), "/")
    })
  })
})
