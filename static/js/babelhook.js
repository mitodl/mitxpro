const { babelSharedLoader } = require("../../webpack.config.shared")

babelSharedLoader.query.presets = ["@babel/env", "@babel/preset-react"]

require("@babel/polyfill")

// window and global must be defined here before React is imported
require("jsdom-global")(undefined, {
  url: "http://fake/"
})

const { polyfill } = require("raf")
polyfill(global)
polyfill(window)

// polyfill for the web crypto module
window.crypto = require("@trust/webcrypto")

// We need to explicitly change the URL when window.location is used
const changeURL = require("jsdom/lib/old-api").changeURL
Object.defineProperty(window, "location", {
  set: value => {
    if (!value.startsWith("http")) {
      value = `http://fake${value}`
    }
    changeURL(window, value)
  }
})

require("@babel/register")(babelSharedLoader.query)
