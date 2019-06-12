// @flow
/* eslint-disable no-unused-vars */

declare type Settings = {
  public_path: string,
  reactGaDebug: string,
  sentry_dsn: string,
  release_version: string,
  environment: string,
  gaTrackingID: ?string,
  recaptchaKey: ?string,
  support_email: string,
  site_name: string,
}
declare var SETTINGS: Settings;

// mocha
declare var it: Function;
declare var beforeEach: Function;
declare var afterEach: Function;
declare var describe: Function;

// webpack
declare var __webpack_public_path__: string; // eslint-disable-line camelcase

declare var module: {
  hot: any,
}
