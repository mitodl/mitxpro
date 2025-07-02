/* global SETTINGS: false */
import { assert } from "chai";
import fetchMock from "fetch-mock";
import sinon from "sinon";

import {
  getCookie,
  fetchJSONWithCSRF,
  fetchWithCSRF,
  csrfSafeMethod,
  patchThing,
} from "./api";
import * as api from "./api";

describe("api", function () {
  this.timeout(5000); // eslint-disable-line no-invalid-this

  let sandbox;
  beforeEach(() => {
    sandbox = sinon.createSandbox({});
  });
  afterEach(function () {
    sandbox.restore();

    for (const cookie of document.cookie.split(";")) {
      const key = cookie.split("=")[0].trim();
      document.cookie = `${key}=`;
    }
  });

  describe("REST functions", () => {
    const THING_RESPONSE = {
      a: "thing",
    };

    let fetchStub;
    beforeEach(() => {
      fetchStub = sandbox.stub(api, "fetchJSONWithCSRF");
    });

    it("patches a thing", () => {
      fetchStub.returns(Promise.resolve(THING_RESPONSE));

      return patchThing("jane", THING_RESPONSE).then((thing) => {
        assert.ok(
          fetchStub.calledWith("/api/v0/thing/jane/", {
            method: "PATCH",
            body: JSON.stringify(THING_RESPONSE),
          }),
        );
        assert.deepEqual(thing, THING_RESPONSE);
      });
    });

    it("fails to patch a thing", () => {
      fetchStub.returns(Promise.reject());
      return patchThing("jane", THING_RESPONSE).catch(() => {
        assert.ok(
          fetchStub.calledWith("/api/v0/thing/jane/", {
            method: "PATCH",
            body: JSON.stringify(THING_RESPONSE),
          }),
        );
      });
    });
  });

  describe("fetch functions", () => {
    const CSRF_TOKEN = "asdf";
    let mock;

    beforeEach(() => {
      mock = fetchMock.mockGlobal();
    });

    afterEach(() => {
      mock.hardReset();
    });

    describe("fetchWithCSRF", () => {
      beforeEach(() => {
        document.cookie = `csrftoken=${CSRF_TOKEN}`;
      });

      it("fetches and populates appropriate headers for GET", () => {
        mock.route(
          {
            method: "GET",
            matcher: "/url",
            functionMatcher: (url, opts) => {
              assert.deepEqual(opts, {
                credentials: "same-origin",
                headers: {},
                method: "GET",
              });
              return true;
            },
          },
          {
            status: 200,
            body: "Some text",
          },
        );

        return fetchWithCSRF("/url").then((responseBody) => {
          assert.equal(responseBody, "Some text");
        });
      });

      for (const method of ["PATCH", "PUT", "POST"]) {
        it(`fetches and populates appropriate headers for ${method}`, () => {
          const body = "body";

          mock.route(
            {
              matcher: "/url",
              method,
              functionMatcher: (url, opts) => {
                assert.deepEqual(opts, {
                  credentials: "same-origin",
                  headers: {
                    "X-CSRFToken": CSRF_TOKEN,
                  },
                  body: body,
                  method: method,
                });
                return true;
              },
            },
            {
              status: 200,
              body: "Some text",
            },
          );

          return fetchWithCSRF("/url", {
            body,
            method,
          }).then((responseBody) => {
            assert.equal(responseBody, "Some text");
          });
        });
      }

      for (const statusCode of [300, 400, 500]) {
        it(`rejects the promise if the status code is ${statusCode}`, () => {
          mock.route(
            {
              method: "GET",
              matcher: "/url",
            },
            {
              status: statusCode,
            },
          );

          return assert.isRejected(fetchWithCSRF("/url"));
        });
      }

      describe("fetchJSONWithCSRF", () => {
        it("fetches and populates appropriate headers for JSON", () => {
          document.cookie = `csrftoken=${CSRF_TOKEN}`;
          const expectedJSON = { data: true };

          mock.route(
            {
              matcher: "/url",
              method: "PATCH",
              functionMatcher: (url, opts) => {
                assert.deepEqual(opts, {
                  credentials: "same-origin",
                  headers: {
                    Accept: "application/json",
                    "Content-Type": "application/json",
                    "X-CSRFToken": CSRF_TOKEN,
                  },
                  body: JSON.stringify(expectedJSON),
                  method: "PATCH",
                });
                return true;
              },
            },
            {
              status: 200,
              body: '{"json": "here"}',
            },
          );

          return fetchJSONWithCSRF("/url", {
            method: "PATCH",
            body: JSON.stringify(expectedJSON),
          }).then((responseBody) => {
            assert.deepEqual(responseBody, {
              json: "here",
            });
          });
        });

        it("handles responses with no data", () => {
          document.cookie = `csrftoken=${CSRF_TOKEN}`;
          const expectedJSON = { data: true };

          mock.route(
            {
              matcher: "/url",
              method: "PATCH",
              functionMatcher: (url, opts) => {
                assert.deepEqual(opts, {
                  credentials: "same-origin",
                  headers: {
                    Accept: "application/json",
                    "Content-Type": "application/json",
                    "X-CSRFToken": CSRF_TOKEN,
                  },
                  body: JSON.stringify(expectedJSON),
                  method: "PATCH",
                });
                return true;
              },
            },
            {
              status: 200,
            },
          );

          return fetchJSONWithCSRF("/url", {
            method: "PATCH",
            body: JSON.stringify(expectedJSON),
          }).then((responseBody) => {
            assert.deepEqual(responseBody, {});
          });
        });

        for (const statusCode of [300, 400, 500]) {
          it(`rejects the promise if the status code is ${statusCode}`, () => {
            mock.route(
              {
                matcher: "/url",
                method: "GET",
              },
              {
                status: statusCode,
                body: JSON.stringify({
                  error: "an error",
                }),
              },
            );

            return assert
              .isRejected(fetchJSONWithCSRF("/url"))
              .then((responseBody) => {
                assert.deepEqual(responseBody, {
                  errorStatusCode: statusCode,
                });
              });
          });
        }

        for (const statusCode of [400, 401]) {
          it(`redirects to login if we set loginOnError and status = ${statusCode}`, () => {
            mock.route(
              {
                matcher: "/url",
                method: "GET",
              },
              () => {
                return { status: statusCode };
              },
            );

            return assert
              .isRejected(fetchJSONWithCSRF("/url", {}, true))
              .then(() => {
                const redirectUrl = `/logout?next=${encodeURIComponent(
                  "/login/edxorg/",
                )}`;
                assert.include(window.location.toString(), redirectUrl);
              });
          });
        }
      });
    });

    describe("getCookie", () => {
      it("gets a cookie", () => {
        document.cookie = "key=cookie";
        assert.equal("cookie", getCookie("key"));
      });

      it("handles multiple cookies correctly", () => {
        document.cookie = "key1=cookie1";
        document.cookie = "key2=cookie2";
        assert.equal("cookie1", getCookie("key1"));
        assert.equal("cookie2", getCookie("key2"));
      });
      it("returns null if cookie not found", () => {
        assert.equal(null, getCookie("unknown"));
      });
    });

    describe("csrfSafeMethod", () => {
      it("knows safe methods", () => {
        for (const method of ["GET", "HEAD", "OPTIONS", "TRACE"]) {
          assert.ok(csrfSafeMethod(method));
        }
      });
      it("knows unsafe methods", () => {
        for (const method of ["PATCH", "PUT", "DELETE", "POST"]) {
          assert.ok(!csrfSafeMethod(method));
        }
      });
    });
  });
});
