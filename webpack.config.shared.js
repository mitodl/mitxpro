const path = require("path")
const webpack = require("webpack")

module.exports = {
  config: {
    entry: {
      root:         ["@babel/polyfill", "./static/js/entry/root"],
      header:       ["@babel/polyfill", "./static/js/entry/header"],
      style:        "./static/js/entry/style",
      django:       ["@babel/polyfill", "./static/js/entry/django"],
    },
    module: {
      rules: [
        {
          test: /\.(svg|ttf|woff|woff2|eot|gif)$/,
          use:  "url-loader"
        },
        {
          test: require.resolve('jquery'),
          use:  [{
            loader:  'expose-loader',
            options: 'jQuery'
          },
          {
            loader:  'expose-loader',
            options: '$'
          }]
        },
        {
          test: require.resolve('hls.js'),
          use:  [{
            loader:  'expose-loader',
            options: 'Hls'
          }]
        }
      ]
    },
    resolve: {
      modules:    [path.join(__dirname, "static/js"), "node_modules"],
      extensions: [".js", ".jsx"]
    },
    performance: {
      hints: false
    }
  },
  babelSharedLoader: {
    test:    /\.jsx?$/,
    include: [
      path.resolve(__dirname, "static/js"),
      path.resolve(__dirname, "node_modules/query-string"),
      path.resolve(__dirname, "node_modules/strict-uri-encode"),
    ],
    loader:  "babel-loader",
    query:   {
      presets: [
        ["@babel/preset-env", { modules: false }],
        "@babel/preset-react",
        "@babel/preset-flow"
      ],
      plugins: [
        "@babel/plugin-transform-flow-strip-types",
        "react-hot-loader/babel",
        "@babel/plugin-proposal-object-rest-spread",
        "@babel/plugin-proposal-class-properties",
        "@babel/plugin-syntax-dynamic-import"
      ]
    }
  }
}
