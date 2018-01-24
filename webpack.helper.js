const path = require('path');
const autoprefixer = require('autoprefixer');
const variables = require('postcss-variables');
const style = require('pv-web-viewer/Utilities/themes/default.js');

module.exports = function (config) {
    config.module.rules.push({
        resource: {
            test: /node_modules(\/|\\)paraviewweb(\/|\\).*.js$/,
            include: [/node_modules(\/|\\)paraviewweb(\/|\\)/]
        },
        use: [{
            loader: 'babel-loader',
            options: {
                presets: ['env', 'react']
            }
        }]
    }, {
        resource: {
            test: /node_modules(\/|\\)pv-web-viewer(\/|\\).*.js$/,
        },
        use: [{
            loader: 'babel-loader',
            options: { presets: ['env', 'react'] }
        }]
    }, {
        resource: {
            test: /ParaViewGlance\.js$/,
        },
        use: [{
            loader: 'babel-loader',
            options: { presets: ['env', 'react'] }
        }]
    }, {
        resource: {
            test: /\.mcss$/,
        },
        use: [
            {
                loader: 'style-loader'
            },
            {
                loader: 'css-loader',
                options: {
                    localIdentName: '[name]-[local]-[sha512:hash:base32:5]',
                    modules: true,
                },
            },
            {
                loader: 'postcss-loader',
                options: {
                    plugins: () => [
                        variables(style),
                        autoprefixer('last 3 version', 'ie >= 10'),
                    ],
                },
            },
        ],
    }, {
        resource: {
            test: /node_modules(\/|\\)vtk\.js(\/|\\).*.glsl$/,
            include: [/node_modules(\/|\\)vtk\.js(\/|\\)/]
        },
        use: [
            'shader-loader'
        ]
    }, {
        resource: {
            test: /node_modules(\/|\\)vtk\.js(\/|\\).*.js$/,
            include: [/node_modules(\/|\\)vtk\.js(\/|\\)/]
        },
        use: [{
            loader: 'babel-loader',
            options: {
                presets: ['env', 'react']
            }
        }]
    });

    config.resolve.alias.PVWStyle = path.resolve('./node_modules/paraviewweb/style');

    return config;
};
