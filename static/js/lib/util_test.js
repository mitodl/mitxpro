// @flow
/* global SETTINGS:false */
import sinon from "sinon"
import { assert } from "chai"
import moment from "moment"

import {
  assertRaises,
  wait,
  enumerate,
  findItemWithTextId,
  isEmptyText,
  preventDefaultAndInvoke,
  notNil,
  truncate,
  getTokenFromUrl,
  makeUUID,
  spaceSeparated,
  formatPrettyDate,
  firstItem,
  secondItem,
  getMinDate,
  getMaxDate,
  newSetWith,
  newSetWithout,
  timeoutPromise,
  getProductSelectLabel,
  isSuccessResponse,
  isErrorResponse,
  isUnauthorizedResponse
} from "./util"
import { makeUserEnrollments } from "../factories/course"
import {
  makeProgramProduct,
  makeCourseRunProduct
} from "../factories/ecommerce"

import { PRODUCT_TYPE_COURSERUN, PRODUCT_TYPE_PROGRAM } from "../constants"

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
    const someNums = function* () {
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

  it("getProductSelectLabel works as expected", () => {
    const program = makeProgramProduct()
    const courseRun = makeCourseRunProduct()

    assert.equal(
      getProductSelectLabel(courseRun),
      `${courseRun.content_object.readable_id} | ${
        courseRun.content_object.title
      } | ${formatPrettyDate(moment(courseRun.content_object.start_date))}`
    )
    assert.equal(
      getProductSelectLabel(program),
      `${program.content_object.readable_id} | ${program.content_object.title}`
    )
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

  describe("assertRaises", () => {
    it("should assert raising an exception", async () => {
      const message = "a message"
      await assertRaises(async () => {
        throw new Error(message)
      }, message)
    })

    it("should raise an error if an exception was not raised", async () => {
      const expectedMessage = "No exception caught"
      let exception
      try {
        await assertRaises(async () => {}, "")
      } catch (ex) {
        exception = ex
      }

      // $FlowFixMe
      assert.equal(exception.message, expectedMessage)
    })

    it("should raise an error if the exception has the wrong message", async () => {
      let exception
      try {
        await assertRaises(async () => {
          throw new Error("other message")
        }, "")
      } catch (ex) {
        exception = ex
      }

      // $FlowFixMe
      assert.equal(exception.message, "expected 'other message' to equal ''")
    })
  })

  it("formatPrettyDate should return a formatted moment date", () => {
    moment.locale("en")
    const momentDate = moment("2019-01-01T00:00:00.000000Z")
    assert.equal(formatPrettyDate(momentDate), "January 1, 2019")
  })

  it("firstItem should return the first item of an array", () => {
    assert.equal(firstItem([1, 2, 3]), 1)
    assert.isUndefined(firstItem([]))
  })

  it("secondItem should return the second item of an array", () => {
    assert.equal(secondItem([1, 2, 3]), 2)
    assert.isUndefined(secondItem([]))
  })

  it("newSetWith returns a set with an additional item", () => {
    const set = new Set([1, 2, 3])
    assert.deepEqual(newSetWith(set, 3), set)
    assert.deepEqual(newSetWith(set, 4), new Set([1, 2, 3, 4]))
  })

  it("newSetWithout returns a set without a specified item", () => {
    const set = new Set([1, 2, 3])
    assert.deepEqual(newSetWithout(set, 3), new Set([1, 2]))
    assert.deepEqual(newSetWithout(set, 4), set)
  })

  it("timeoutPromise returns a Promise that executes a function after a delay then resolves", async () => {
    const func = sinon.stub()
    const promise = timeoutPromise(func, 10)
    sinon.assert.callCount(func, 0)
    await promise
    sinon.assert.callCount(func, 1)
  })

  describe("dateFunction", () => {
    const futureDate = moment().add(7, "days"),
      pastDate = moment().add(-7, "days"),
      now = moment()

    it("getMinDate returns the earliest date of a list of dates or null", () => {
      let dates = [futureDate, pastDate, now, now, undefined, null]
      assert.equal(getMinDate(dates).toISOString(), pastDate.toISOString())
      dates = [null, undefined]
      assert.isNull(getMinDate(dates))
    })

    it("getMaxDate returns the latest date of a list of dates or null", () => {
      let dates = [futureDate, pastDate, now, now, undefined, null]
      assert.equal(getMaxDate(dates).toISOString(), futureDate.toISOString())
      dates = [null, undefined]
      assert.isNull(getMaxDate(dates))
    })
  })

  describe("findItemWithTextId", () => {
    it("finds the readable id for a program", () => {
      const enrollments = makeUserEnrollments()
      const program = enrollments.program_enrollments[0].program
      assert.deepEqual(
        findItemWithTextId(enrollments, program.readable_id),
        program
      )
    })

    it("finds the readable id for a course in a program", () => {
      const enrollments = makeUserEnrollments()
      const run =
        enrollments.program_enrollments[0].course_run_enrollments[1].run
      assert.deepEqual(findItemWithTextId(enrollments, run.courseware_id), run)
    })

    it("finds the readable id for a course outside a program", () => {
      const enrollments = makeUserEnrollments()
      const run = enrollments.course_run_enrollments[1].run
      assert.deepEqual(findItemWithTextId(enrollments, run.courseware_id), run)
    })

    it("can't find the readable id so it returns null", () => {
      const enrollments = makeUserEnrollments()
      assert.isNull(findItemWithTextId(enrollments, "missing"))
    })
  })

  //
  ;[[200, false], [299, false], [300, false], [400, true], [500, true]].forEach(
    ([status, expResult]) => {
      it(`isErrorResponse returns ${String(expResult)} when status=${String(
        status
      )}`, () => {
        const response = {
          status: status,
          body:   {}
        }
        assert.equal(isErrorResponse(response), expResult)
      })
    }
  )

  //
  ;[[200, true], [299, true], [300, false], [400, false], [500, false]].forEach(
    ([status, expResult]) => {
      it(`isSuccessResponse returns ${String(expResult)} when status=${String(
        status
      )}`, () => {
        const response = {
          status: status,
          body:   {}
        }
        assert.equal(isSuccessResponse(response), expResult)
      })
    }
  )

  //
  ;[[401, true], [403, true], [200, false], [400, false], [500, false]].forEach(
    ([status, expResult]) => {
      it(`isUnauthorizedResponse returns ${String(
        expResult
      )} when status=${String(status)}`, () => {
        const response = {
          status: status,
          body:   {}
        }
        assert.equal(isUnauthorizedResponse(response), expResult)
      })
    }
  )
})
