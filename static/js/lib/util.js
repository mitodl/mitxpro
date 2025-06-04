// @flow
/* global SETTINGS:false */
import React from "react";
import {
  all,
  complement,
  compose,
  curry,
  defaultTo,
  either,
  isEmpty,
  isNil,
  lensPath,
  trim,
  view,
} from "ramda";
import _truncate from "lodash/truncate";
import qs from "query-string";
import * as R from "ramda";
import moment from "moment";
import { Link } from "react-router-dom";
import posthog from "posthog-js";

import type Moment from "moment";
import type {
  CourseRunDetail,
  Program,
  UserEnrollments,
} from "../flow/courseTypes";

import type { Product } from "../flow/ecommerceTypes";

import { PRODUCT_TYPE_COURSERUN } from "../constants";
import type { HttpRespErrorMessage, HttpResponse } from "../flow/httpTypes";
import { routes } from "./urls";
import {
  STATE_INVALID_EMAIL,
  STATE_INVALID_LINK,
  STATE_EXISTING_ACCOUNT,
} from "./auth";

if (SETTINGS.posthog_api_host && SETTINGS.posthog_api_token) {
  const environment = SETTINGS.environment;
  if (environment === "dev") {
    posthog.debug();
  }
  posthog.init(SETTINGS.posthog_api_token, {
    api_host: SETTINGS.posthog_api_host,
    autocapture: false,
    capture_pageview: false,
    capture_pageleave: false,
    cross_subdomain_cookie: false,
    persistence: "localStorage+cookie",
    loaded: function (posthog) {
      posthog.setPersonPropertiesForFlags({
        environment: environment,
      });
    },
  });
}

/**
 * Returns a promise which resolves after a number of milliseconds have elapsed
 */
export const wait = (millis: number): Promise<void> =>
  new Promise((resolve) => setTimeout(resolve, millis));

/**
 * Adds on an index for each item in an iterable
 */
export function* enumerate<T>(
  iterable: Iterable<T>,
): Generator<[number, T], void, void> {
  let i = 0;
  for (const item of iterable) {
    yield [i, item];
    ++i;
  }
}

export const isEmptyText = compose(isEmpty, trim, defaultTo(""));

export const notNil = complement(isNil);

export const goBackAndHandleEvent = curry((history, e) => {
  e.preventDefault();
  history.goBack();
});

export const preventDefaultAndInvoke = curry((invokee: Function, e: Event) => {
  if (e) {
    e.preventDefault();
  }
  invokee();
});

export const truncate = (text: ?string, length: number): string =>
  text ? _truncate(text, { length: length, separator: " " }) : "";

export const getTokenFromUrl = (props: Object): string => {
  const urlMatchPath = ["match", "params", "token"],
    querystringPath = ["location", "search"];

  let token = view(lensPath(urlMatchPath))(props);
  if (token) return token;

  const querystring = view(lensPath(querystringPath))(props);
  const parsedQuerystring = qs.parse(querystring);
  token = parsedQuerystring.token;
  return token || "";
};

export const makeUUID = (len: number) =>
  Array.from(window.crypto.getRandomValues(new Uint8Array(len)))
    .map((int) => int.toString(16))
    .join("")
    .slice(0, len);

export const removeTrailingSlash = (str: string) =>
  str.length > 0 && str[str.length - 1] === "/"
    ? str.substr(0, str.length - 1)
    : str;

export const emptyOrNil = either(isEmpty, isNil);
export const allEmptyOrNil = all(emptyOrNil);
export const anyNil = R.any(R.isNil);

export const spaceSeparated = (strings: Array<?string>): string =>
  strings.filter((str) => str).join(" ");

export function* incrementer(): Generator<number, *, *> {
  let int = 1;
  // eslint-disable-next-line no-constant-condition
  while (true) {
    yield int++;
  }
}

export const toArray = (obj: any) =>
  Array.isArray(obj) ? obj : obj ? [obj] : undefined;

// Example return values: "January 1, 2019", "December 31, 2019"
export const formatPrettyDate = (momentDate: Moment) =>
  momentDate.format("MMMM D, YYYY");

export const formatPrettyDateTimeAmPm = (momentDate: Moment) =>
  momentDate.format("LLL");

export const firstItem = R.view(R.lensIndex(0));

export const secondItem = R.view(R.lensIndex(1));

export const parseDateString = (dateString: ?string): ?Moment =>
  emptyOrNil(dateString) ? undefined : moment(dateString);

const getDateExtreme = R.curry(
  (compareFunc: Function, momentDates: Array<?Moment>): ?Moment => {
    const filteredDates = R.reject(R.isNil, momentDates);
    if (filteredDates.length === 0) {
      return null;
    }
    return R.compose(moment, R.apply(compareFunc))(filteredDates);
  },
);

export const getMinDate = getDateExtreme(Math.min);
export const getMaxDate = getDateExtreme(Math.max);

export const newSetWith = (set: Set<*>, valueToAdd: any): Set<*> => {
  const newSet = new Set(set);
  newSet.add(valueToAdd);
  return newSet;
};

export const newSetWithout = (set: Set<*>, valueToDelete: any): Set<*> => {
  const newSet = new Set(set);
  newSet.delete(valueToDelete);
  return newSet;
};

/**
 * Returns a Promise that executes a function after a given number of milliseconds then resolves
 */
export const timeoutPromise = (
  funcToExecute: Function,
  timeoutMs: number,
): Promise<*> => {
  return new Promise((resolve) =>
    setTimeout(() => {
      funcToExecute();
      resolve();
    }, timeoutMs),
  );
};

export const findItemWithTextId = (
  enrollments: UserEnrollments,
  textId: ?string,
): Program | CourseRunDetail | null => {
  for (const programEnrollment of enrollments.program_enrollments) {
    if (textId === programEnrollment.program.readable_id) {
      return programEnrollment.program;
    }

    for (const courseRunEnrollment of programEnrollment.course_run_enrollments) {
      if (textId === courseRunEnrollment.run.courseware_id) {
        return courseRunEnrollment.run;
      }
    }
  }

  for (const courseRunEnrollment of enrollments.course_run_enrollments) {
    if (textId === courseRunEnrollment.run.courseware_id) {
      return courseRunEnrollment.run;
    }
  }

  return null;
};

export const getProductSelectLabel = (product: Product) => {
  const label = `${product.content_object.readable_id} | ${product.content_object.title}`;
  if (
    product.product_type === PRODUCT_TYPE_COURSERUN &&
    product.content_object.start_date !== null
  ) {
    return `${label} | ${formatPrettyDate(
      moment(product.content_object.start_date),
    )}`;
  } else {
    return label;
  }
};

export const sameDayOrLater = (
  momentDate1: Moment,
  momentDate2: Moment,
): boolean =>
  momentDate1.startOf("day").isSameOrAfter(momentDate2.startOf("day"));

export const isSuccessResponse = (response: HttpResponse<*>): boolean =>
  response.status >= 200 && response.status < 300;

export const isErrorResponse = (response: HttpResponse<*>): boolean =>
  response.status === 0 || response.status >= 400;

export const isUnauthorizedResponse = (response: HttpResponse<*>): boolean =>
  response.status === 401 || response.status === 403;

export const getErrorMessages = (
  response: HttpResponse<*>,
): HttpRespErrorMessage => {
  if (!response.body || !response.body.errors) {
    return null;
  }
  return response.body.errors;
};

export const getAppropriateInformationFragment = (state: string) => {
  let preLinkText = "";
  let postLinkText = "";
  let linkRoute = null;
  if (state === STATE_INVALID_LINK) {
    preLinkText = "This invitation is invalid or has expired. Please";
    postLinkText = "to register again";
    linkRoute = routes.register.begin;
  } else if (state === STATE_EXISTING_ACCOUNT) {
    preLinkText = "You already have an xPRO account. Please";
    postLinkText = "to sign in";
    linkRoute = routes.login.begin;
  } else if (state === STATE_INVALID_EMAIL) {
    preLinkText = "No confirmation code was provided or it has expired.";
    postLinkText = "to register again";
    linkRoute = routes.register.begin;
  }
  return (
    <React.Fragment>
      <span className={"confirmation-message"}>
        {preLinkText}{" "}
        <Link className={"action-link"} to={linkRoute}>
          click here {postLinkText}
        </Link>
        .
      </span>
    </React.Fragment>
  );
};

export const zeroHour = (value) => {
  if (value instanceof Date) {
    value.setHours(0, 0, 0, 0);
  }
};

export const finalHour = (value) => {
  if (value instanceof Date) {
    value.setHours(23, 59, 59, 999);
  }
};
