// @flow
/* global SETTINGS:false */
import {
  isEmpty,
  trim,
  defaultTo,
  view,
  lensPath,
  either,
  all,
  curry,
  complement,
  compose,
  isNil
} from "ramda"
import { truncate as _truncate } from "lodash"
import qs from "query-string"

/**
 * Returns a promise which resolves after a number of milliseconds have elapsed
 */
export const wait = (millis: number): Promise<void> =>
  new Promise(resolve => setTimeout(resolve, millis))

/**
 * Adds on an index for each item in an iterable
 */
export function* enumerate<T>(
  iterable: Iterable<T>
): Generator<[number, T], void, void> {
  let i = 0
  for (const item of iterable) {
    yield [i, item]
    ++i
  }
}

export const isEmptyText = compose(
  isEmpty,
  trim,
  defaultTo("")
)

export const notNil = complement(isNil)

export const goBackAndHandleEvent = curry((history, e) => {
  e.preventDefault()
  history.goBack()
})

export const preventDefaultAndInvoke = curry((invokee: Function, e: Event) => {
  if (e) {
    e.preventDefault()
  }
  invokee()
})

export const truncate = (text: ?string, length: number): string =>
  text ? _truncate(text, { length: length, separator: " " }) : ""

export const getTokenFromUrl = (props: Object): string => {
  const urlMatchPath = ["match", "params", "token"],
    querystringPath = ["location", "search"]

  let token = view(lensPath(urlMatchPath))(props)
  if (token) return token

  const querystring = view(lensPath(querystringPath))(props)
  const parsedQuerystring = qs.parse(querystring)
  token = parsedQuerystring.token
  return token || ""
}

export const makeUUID = (len: number) =>
  Array.from(window.crypto.getRandomValues(new Uint8Array(len)))
    .map(int => int.toString(16))
    .join("")
    .slice(0, len)

export const removeTrailingSlash = (str: string) =>
  str.length > 0 && str[str.length - 1] === "/"
    ? str.substr(0, str.length - 1)
    : str

export const emptyOrNil = either(isEmpty, isNil)
export const allEmptyOrNil = all(emptyOrNil)

export const spaceSeparated = (strings: Array<?string>): string =>
  strings.filter(str => str).join(" ")

export function* incrementer(): Generator<number, *, *> {
  let int = 1
  // eslint-disable-next-line no-constant-condition
  while (true) {
    yield int++
  }
}

export const toArray = (obj: any) =>
  Array.isArray(obj) ? obj : obj ? [obj] : undefined
