const path = require("path");
const webpack = require("webpack");

module.exports = {
  config: {
    entry: {
      'root': ['babel-polyfill', './static/js/entry/root'],
      'style': './static/js/entry/style',
    },
    module: {
      rules: [
        {
          test: /\.(svg|ttf|woff|woff2|eot|gif)$/,
          use: 'url-loader'
        },
      ]
    },
    resolve: {
      modules: [
        path.join(__dirname, "static/js"),
        "node_modules"
      ],
      extensions: ['.js', '.jsx'],
    },
    performance: {
      hints: false
    }
  },
  babelSharedLoader: {
    test: /\.jsx?$/,
    exclude: /node_modules/,
    loader: 'babel-loader',
    query: {
      "presets": [
        ["env", { "modules": false }],
        "react",
      ],
      "ignore": [
        "node_modules/**"
      ],
      "plugins": [
        "transform-flow-strip-types",
        "react-hot-loader/babel",
        "transform-object-rest-spread",
        "transform-class-properties",
        "syntax-dynamic-import",
      ]
    }
  },
};
