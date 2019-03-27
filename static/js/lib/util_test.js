// @flow
/* global SETTINGS:false */
import sinon from "sinon"
import { assert } from "chai"

import {
  wait,
  enumerate,
  isEmptyText,
  preventDefaultAndInvoke,
  notNil,
  truncate,
  getTokenFromUrl,
  makeUUID,
  spaceSeparated
} from "./util"

describe("utility functions", () => {
  it("waits some milliseconds", done => {
    let executed = false
    wait(30).then(() => {
      executed = true
    })

    setTimeout(() => {
      assert.isFalse(executed)

      setTimeout(() => {
        assert.isTrue(executed)

        done()
      }, 20)
    }, 20)
  })

  it("enumerates an iterable", () => {
    const someNums = function*() {
      yield* [6, 7, 8, 9, 10]
    }

    const list = []
    for (const item of enumerate(someNums())) {
      list.push(item)
    }

    assert.deepEqual(list, [[0, 6], [1, 7], [2, 8], [3, 9], [4, 10]])
  })

  it("isEmptyText works as expected", () => {
    [
      [" ", true],
      ["", true],
      ["\n\t   ", true],
      ["                   \t ", true],
      ["foo \n", false],
      ["foo", false],
      ["   \n\tfoo", false]
    ].forEach(([text, exp]) => {
      assert.equal(isEmptyText(text), exp)
    })
  })

  it("truncate works as expected", () => {
    [
      ["", ""],
      [null, ""],
      ["A random string", "A random string"],
      ["A random string with many words.", "A random string..."]
    ].forEach(([text, expected]) => {
      assert.equal(truncate(text, 20), expected)
    })
  })

  it("preventDefaultAndInvoke works as expected", () => {
    const invokee = sinon.stub()
    const event = {
      preventDefault: sinon.stub()
    }

    preventDefaultAndInvoke(invokee, event)

    sinon.assert.calledWith(invokee)
    sinon.assert.calledWith(event.preventDefault)
  })

  it("notNil works as expected", () => {
    [
      [null, false],
      [undefined, false],
      [0, true],
      ["", true],
      ["abc", true]
    ].forEach(([val, exp]) => {
      assert.equal(notNil(val), exp)
    })
  })

  it("getTokenFromUrl gets a token value from a url match or the querystring", () => {
    [
      ["url_token", undefined, "url_token"],
      [undefined, "?token=querystring_token", "querystring_token"],
      ["url_token", "?token=querystring_token", "url_token"],
      [undefined, "?not_token=whatever", ""],
      [undefined, undefined, ""]
    ].forEach(([urlMatchTokenValue, querystringValue, exp]) => {
      const props = {
        match: {
          params: {
            token: urlMatchTokenValue
          }
        },
        location: {
          search: querystringValue
        }
      }
      const token = getTokenFromUrl(props)
      assert.equal(token, exp)
    })
  })

  describe("makeUUID", () => {
    it("should return a string", () => {
      const uuid = makeUUID(10)
      assert.isString(uuid)
    })

    it("should be as long as you specify", () => {
      [10, 11, 12, 20, 3].forEach(len => {
        assert.equal(makeUUID(len).length, len)
      })
    })

    it("it uhh shouldnt return the same thing twice :D", () => {
      assert.notEqual(makeUUID(10), makeUUID(10))
    })
  })

  describe("spaceSeparated", () => {
    it("should return a space separated string when given an array of strings or nulls", () => {
      [
        [["a", "b", "c"], "a b c"],
        [[null, null], ""],
        [[null, "a", "b"], "a b"],
        [["a", "b", null], "a b"]
      ].forEach(([inputArr, expectedStr]) => {
        assert.deepEqual(spaceSeparated(inputArr), expectedStr)
      })
    })
  })
})
