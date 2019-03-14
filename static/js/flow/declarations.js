// @flow
/* eslint-disable no-unused-vars */
declare var SETTINGS: {
  public_path: string,
  FEATURES: {
    [key: string]: boolean,
  },
  reactGaDebug: string,
  sentry_dsn: string,
  release_version: string,
  environment: string,
  gaTrackingID: ?string
};

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
