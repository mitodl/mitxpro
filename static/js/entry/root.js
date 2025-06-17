import React from "react";
import ReactDOM from "react-dom";
import { AppContainer } from "react-hot-loader";
import { createBrowserHistory } from "history";

import configureStore from "../store/configureStore";
import Router, { routes } from "../Router";
import { AppTypeContext, SPA_APP_CONTEXT } from "../contextDefinitions";

import * as Sentry from "@sentry/browser";
// Object.entries polyfill
import entries from "object.entries";

require("react-hot-loader/patch");
/* global SETTINGS:false */
__webpack_public_path__ = SETTINGS.public_path; // eslint-disable-line no-undef, camelcase

Sentry.init({
  dsn: SETTINGS.sentry_dsn,
  release: SETTINGS.release_version,
  environment: SETTINGS.environment,
});

if (!Object.entries) {
  entries.shim();
}

const store = configureStore();

const rootEl = document.getElementById("container");

const renderApp = (Component) => {
  const history = createBrowserHistory();
  ReactDOM.render(
    <AppContainer>
      <AppTypeContext.Provider value={SPA_APP_CONTEXT}>
        <Component history={history} store={store}>
          {routes}
        </Component>
      </AppTypeContext.Provider>
    </AppContainer>,
    rootEl,
  );
};

renderApp(Router);

if (module.hot) {
  module.hot.accept("../Router", () => {
    const RouterNext = require("../Router").default;
    renderApp(RouterNext);
  });
}
