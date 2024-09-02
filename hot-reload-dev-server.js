const path = require("path");
const webpack = require("webpack");
const express = require("express");
const devMiddleware = require("webpack-dev-middleware");
const hotMiddleware = require("webpack-hot-middleware");
const minimist = require("minimist");

const { makeDevConfig } = require("./webpack.config.dev");

const { host, port } = minimist(process.argv.slice(2));

const config = makeDevConfig(host, port);

const app = express();

const compiler = webpack(config);

app.use(function (req, res, next) {
  res.header("Access-Control-Allow-Origin", "*");
  next();
});

app.use(
  devMiddleware(compiler, {
    publicPath: process.env.PUBLIC_PATH
  }),
);

app.use(hotMiddleware(compiler));

app.listen(port, (err) => {
  if (err) {
    return console.error(err);
  }
  console.log(`listening at http://${host}:${port}`);
  console.log("building...");
});
