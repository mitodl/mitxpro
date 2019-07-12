const { babelSharedLoader } = require("../../webpack.config.shared")

babelSharedLoader.query.presets = ["@babel/env", "@babel/preset-react"]

require("@babel/polyfill")

// jsdom initialization here adapted from from https://airbnb.io/enzyme/docs/guides/jsdom.html
const { JSDOM } = require("jsdom")
const jsdom = new JSDOM("<!doctype html><html><body></body></html>")
const { window } = jsdom

const { polyfill } = require("raf")
polyfill(global)
polyfill(window)

// polyfill for the web crypto module
window.crypto = require("@trust/webcrypto")

// We need to explicitly change the URL when window.location is used

function copyProps(src, target) {
  Object.defineProperties(target, {
    ...Object.getOwnPropertyDescriptors(src),
    ...Object.getOwnPropertyDescriptors(target)
  })
}

global.window = window
global.document = window.document
global.navigator = {
  userAgent: "node.js"
}
global.requestAnimationFrame = function(callback) {
  return setTimeout(callback, 0)
}
global.cancelAnimationFrame = function(id) {
  clearTimeout(id)
}
copyProps(window, global)

Object.defineProperty(window, "location", {
  set: value => {
    if (!value.startsWith("http")) {
      value = `http://fake${value}`
    }
    jsdom.reconfigure({ url: value })
  }
})

require("@babel/register")(babelSharedLoader.query)
