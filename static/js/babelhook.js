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

// jsdom 31+ brand-checks `this` on Window methods, so calling them through
// the Proxy below (e.g. window.addEventListener) throws. Bind jsdom's own
// methods to the real window. Functions assigned later (e.g. sinon stubs)
// are returned as-is so stubbing and restoring keep working.
const nativeMethods = new Set();
for (let obj = window; obj; obj = Object.getPrototypeOf(obj)) {
  for (const name of Object.getOwnPropertyNames(obj)) {
    const { value } = Object.getOwnPropertyDescriptor(obj, name);
    if (typeof value === "function" && !/^[A-Z]/.test(name)) {
      nativeMethods.add(value);
    }
  }
}
const boundMethods = new WeakMap();

// Proxy window.location assignments to use jsdom.reconfigure()
// instead of direct assignment, which is no longer allowed in v26
const windowProxy = new Proxy(window, {
  get: function (target, prop) {
    const value = Reflect.get(target, prop, target);
    if (!nativeMethods.has(value)) {
      return value;
    }
    if (!boundMethods.has(value)) {
      boundMethods.set(value, value.bind(target));
    }
    return boundMethods.get(value);
  },
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
