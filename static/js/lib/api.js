// @flow
/* global SETTINGS:false */
import "isomorphic-fetch"
import * as R from "ramda"

import { S, parseJSON, filterE } from "./sanctuary"

export function getCookie(name: string): string | null {
  let cookieValue = null

  if (document.cookie && document.cookie !== "") {
    const cookies = document.cookie.split(";")

    for (let cookie of cookies) {
      cookie = cookie.trim()

      // Does this cookie string begin with the name we want?
      if (cookie.substring(0, name.length + 1) === `${name}=`) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1))
        break
      }
    }
  }
  return cookieValue
}

export function csrfSafeMethod(method: string): boolean {
  // these HTTP methods do not require CSRF protection
  return /^(GET|HEAD|OPTIONS|TRACE)$/.test(method)
}

const headers = R.merge({ headers: {} })

const method = R.merge({ method: "GET" })

const credentials = R.merge({ credentials: "same-origin" })

const setWith = R.curry((path, valFunc, obj) => R.set(path, valFunc(), obj))

const csrfToken = R.unless(
  R.compose(
    csrfSafeMethod,
    R.prop("method")
  ),
  setWith(R.lensPath(["headers", "X-CSRFToken"]), () => getCookie("csrftoken"))
)

const jsonHeaders = R.merge({
  headers: {
    "Content-Type": "application/json",
    Accept:         "application/json"
  }
})

const formatRequest = R.compose(
  csrfToken,
  credentials,
  method,
  headers
)

const formatJSONRequest = R.compose(
  formatRequest,
  jsonHeaders
)

const _fetchWithCSRF = async (path: string, init: Object = {}): Promise<*> => {
  const response = await fetch(path, formatRequest(init))
  const text = await response.text()

  if (response.status < 200 || response.status >= 300) {
    return Promise.reject([text, response.status])
  }
  return text
}

export { _fetchWithCSRF as fetchWithCSRF }

// resolveEither :: Either -> Promise
// if the Either is a Left, returns Promise.reject(val)
// if the Either is a Right, returns Promise.resolve(val)
// where val is the unwrapped value in the Either
const resolveEither = S.either(
  val => Promise.reject(val),
  val => Promise.resolve(val)
)

const handleEmptyJSON = json => (json.length === 0 ? JSON.stringify({}) : json)

/**
 * Calls to fetch but does a few other things:
 *  - turn cookies on for this domain
 *  - set headers to handle JSON properly
 *  - handle CSRF
 *  - non 2xx status codes will reject the promise returned
 *  - response JSON is returned in place of response
 */
const _fetchJSONWithCSRF = async (
  input: string,
  init: Object = {},
  loginOnError: boolean = false
): Promise<*> => {
  const response = await fetch(input, formatJSONRequest(init))
  // For 400 and 401 errors, force login
  // the 400 error comes from edX in case there are problems with the refresh
  // token because the data stored locally is wrong and the solution is only
  // to force a new login
  if (
    loginOnError === true &&
    (response.status === 400 || response.status === 401)
  ) {
    const relativePath = window.location.pathname + window.location.search
    const loginRedirect = `/login/edxorg/?next=${encodeURIComponent(
      relativePath
    )}`
    window.location = `/logout?next=${encodeURIComponent(loginRedirect)}`
  }

  // we pull the text out of the response
  const text = await response.text()

  // Here we use the `parseJSON` function, which returns an Either.
  // Left records an error parsing the JSON, and Right success. `filterE` will turn a Right
  // into a Left based on a boolean function (similar to filtering a Maybe), and we use `bimap`
  // to merge an error code into a Left. The `resolveEither` function above will resolve a Right
  // and reject a Left.
  return R.compose(
    resolveEither,
    S.bimap(R.merge({ errorStatusCode: response.status }), R.identity),
    filterE(() => response.ok),
    parseJSON,
    handleEmptyJSON
  )(text)
}

// allow mocking in tests
export { _fetchJSONWithCSRF as fetchJSONWithCSRF }
import { fetchJSONWithCSRF } from "./api"

// import to allow mocking in tests
export function patchThing(username: string, newThing: Object) {
  return fetchJSONWithCSRF(`/api/v0/thing/${username}/`, {
    method: "PATCH",
    body:   JSON.stringify(newThing)
  })
}
