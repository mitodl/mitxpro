const { babelSharedLoader } = require("../../webpack.config.shared");

babelSharedLoader.options.presets = ["@babel/env", "@babel/preset-react"];

require("@babel/polyfill");

// jsdom initialization here adapted from from https://airbnb.io/enzyme/docs/guides/jsdom.html
const { JSDOM } = require("jsdom");
const jsdom = new JSDOM("<!doctype html><html><body></body></html>");
const { window } = jsdom;

const { polyfill } = require("raf");
polyfill(global);
polyfill(window);

// polyfill for the web crypto module
window.crypto = require("@trust/webcrypto");

// We need to explicitly change the URL when window.location is used

function copyProps(src, target) {
  Object.defineProperties(target, {
    ...Object.getOwnPropertyDescriptors(src),
    ...Object.getOwnPropertyDescriptors(target),
  });
}

const windowProxy = new Proxy(window, {
  set: function (target, prop, value) {
    if (prop === "location") {
      let url = value;
      if (!url.startsWith("http")) {
        url = `http://fake${url}`;
      }
      jsdom.reconfigure({ url });
      return true;
    }

    return Reflect.set(target, prop, value);
  },
});

global.window = windowProxy;
global.document = windowProxy.document;
global.navigator = {
  userAgent: "node.js",
};
global.requestAnimationFrame = function (callback) {
  return setTimeout(callback, 0);
};
global.cancelAnimationFrame = function (id) {
  clearTimeout(id);
};
copyProps(window, global);

require("@babel/register")(babelSharedLoader.options);
