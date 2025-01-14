// @flow
/* eslint-disable no-unused-vars */

declare type Settings = {
  public_path: string,
  reactGaDebug: string,
  sentry_dsn: string,
  release_version: string,
  environment: string,
  gtmTrackingID: ?string,
  gaTrackingID: ?string,
  recaptchaKey: ?string,
  support_email: string,
  site_name: string,
  zendesk_config: {
    help_widget_enabled: boolean,
    help_widget_key: ?string,
  },
  digital_credentials: boolean,
  digital_credentials_supported_runs: Array<string>,
  is_tax_applicable: boolean,
  enable_enterprise: boolean,
  posthog_api_token: ?string,
  posthog_api_host: ?string
};
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
};
