// @flow
/* global SETTINGS:false */
import "isomorphic-fetch";
import * as R from "ramda";

export function getCookie(name: string): string | null {
  let cookieValue = null;

  if (document.cookie && document.cookie !== "") {
    const cookies = document.cookie.split(";");

    for (let cookie of cookies) {
      cookie = cookie.trim();

      // Does this cookie string begin with the name we want?
      if (cookie.substring(0, name.length + 1) === `${name}=`) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

export function csrfSafeMethod(method: string): boolean {
  // these HTTP methods do not require CSRF protection
  return /^(GET|HEAD|OPTIONS|TRACE)$/.test(method);
}

const headers = R.merge({ headers: {} });

const method = R.merge({ method: "GET" });

const credentials = R.merge({ credentials: "same-origin" });

const setWith = R.curry((path, valFunc, obj) => R.set(path, valFunc(), obj));

const csrfToken = R.unless(
  R.compose(csrfSafeMethod, R.prop("method")),
  setWith(R.lensPath(["headers", "X-CSRFToken"]), () => getCookie("csrftoken")),
);

const jsonHeaders = R.merge({
  headers: {
    "Content-Type": "application/json",
    Accept: "application/json",
  },
});

const formatRequest = R.compose(csrfToken, credentials, method, headers);

const formatJSONRequest = R.compose(formatRequest, jsonHeaders);

const _fetchWithCSRF = async (path: string, init: Object = {}): Promise<*> => {
  const response = await fetch(path, formatRequest(init));
  const text = await response.text();

  if (response.status < 200 || response.status >= 300) {
    return Promise.reject([text, response.status]);
  }
  return text;
};

export { _fetchWithCSRF as fetchWithCSRF };

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
  loginOnError: boolean = false,
): Promise<*> => {
  const response = await fetch(input, formatJSONRequest(init));
  // For 400 and 401 errors, force login
  // the 400 error comes from edX in case there are problems with the refresh
  // token because the data stored locally is wrong and the solution is only
  // to force a new login
  if (
    loginOnError === true &&
    (response.status === 400 || response.status === 401)
  ) {
    const relativePath = window.location.pathname + window.location.search;
    const loginRedirect = `/login/edxorg/?next=${encodeURIComponent(
      relativePath,
    )}`;
    window.location = `/logout?next=${encodeURIComponent(loginRedirect)}`;
  }

  let json;
  try {
    json = await response.json();
  } catch {
    json = {};
  }

  if (response.ok) {
    return json;
  } else {
    json.errorStatusCode = response.status;
    throw json;
  }
};

// allow mocking in tests
export { _fetchJSONWithCSRF as fetchJSONWithCSRF };
import { fetchJSONWithCSRF } from "./api";

// import to allow mocking in tests
export function patchThing(username: string, newThing: Object) {
  return fetchJSONWithCSRF(`/api/v0/thing/${username}/`, {
    method: "PATCH",
    body: JSON.stringify(newThing),
  });
}
