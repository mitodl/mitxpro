const webpack = require("webpack");
const path = require("path");
const BundleTracker = require("webpack-bundle-tracker");
const MiniCssExtractPlugin = require("mini-css-extract-plugin");
const { config, babelSharedLoader } = require(
  path.resolve("./webpack.config.shared.js"),
);
const { BundleAnalyzerPlugin } = require("webpack-bundle-analyzer");

const prodBabelConfig = Object.assign({}, babelSharedLoader);

prodBabelConfig.options.plugins.push(
  "@babel/plugin-transform-react-constant-elements",
  "@babel/plugin-transform-react-inline-elements",
);

const prodConfig = Object.assign({}, config);
prodConfig.module.rules = [
  prodBabelConfig,
  ...config.module.rules,
  {
    test: /\.css$|\.scss$/,
    use: [
      {
        loader: MiniCssExtractPlugin.loader,
      },
      "css-loader",
      "postcss-loader",
      "sass-loader",
    ],
  },
];

const analyzeBundles = process.env.WEBPACK_ANALYZE?.toLowerCase() === "true";

module.exports = Object.assign(prodConfig, {
  context: __dirname,
  mode: "production",
  output: {
    path: path.resolve("./static/bundles/"),
    filename: "[name]-[chunkhash].js",
    chunkFilename: "[id]-[chunkhash].js",
    crossOriginLoading: "anonymous",
    publicPath: "/static/bundles",
  },

  plugins: [
    new BundleTracker({
      filename: "./webpack-stats.json",
    }),
    new webpack.LoaderOptionsPlugin({
      minimize: true,
    }),
    new webpack.optimize.AggressiveMergingPlugin(),
    new MiniCssExtractPlugin({
      filename: "[name]-[contenthash].css",
    }),
    ...(analyzeBundles
      ? [
          new BundleAnalyzerPlugin({
            analyzerMode: "static",
          }),
        ]
      : []),
  ],
  optimization: {
    minimize: true,
    moduleIds: "named",
    splitChunks: {
      name: "common",
      minChunks: 2,
      automaticNameDelimiter: "-",
      cacheGroups: {
        common: {
          test: /[\\/]node_modules[\\/]/,
          name: "common",
          chunks: "all",
        },
      },
    },
  },
  devtool: "source-map",
});
