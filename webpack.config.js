const webpack = require('webpack');
const path = require('path');

const entry = path.join(__dirname, './src/index.js');
const sourcePath = path.join(__dirname, './src');
const outputPath = path.join(__dirname, './dist');
const eslintrcPath = path.join(__dirname, './.eslintrc.js');

module.exports = {
  entry,
  output: {
    path: outputPath,
    filename: 'dynanail.js',
  },
  module: {
    rules: [
      { test: entry, loader: 'expose-loader?dynanail' },
      {
        test: /\.js$/,
        use: [
          { loader: 'babel-loader', options: { presets: ['es2015'] } },
        ],
      },
      {
        test: /\.js$/,
        include: /node_modules(\/|\\)paraviewweb(\/|\\)/,
        use: [
          { loader: 'babel-loader', options: { presets: ['es2015'] } },
        ],
      },
      { test: /\.js$/, loader: 'eslint-loader', exclude: /node_modules/, enforce: 'pre', options: { configFile: eslintrcPath } },
    ],
  },
  devServer: {
    contentBase: path.resolve(__dirname, 'dist'),
    port: 9999,
    host: 'localhost',
    disableHostCheck: true,
    hot: false,
    quiet: false,
    noInfo: false,
    stats: {
      colors: true,
    },
  },
};
