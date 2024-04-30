// @flow
import { assert } from "chai";

import { getNextParam } from "./urls";

describe("url libraries", () => {
  describe("getNextParam", () => {
    it("should return a default value if no next param", () => {
      assert.equal(getNextParam(""), "/");
    });
    it("should return the next param when present", () => {
      const next = "/next/url";
      assert.equal(getNextParam(`?next=${encodeURIComponent(next)}`), next);
    });
  });
});
