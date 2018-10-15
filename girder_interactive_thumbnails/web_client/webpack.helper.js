module.exports = function (config) {
    config.module.rules.push({
        resource: {
            test: /node_modules(\/|\\)paraviewweb(\/|\\).*.js$/,
            include: [/node_modules(\/|\\)paraviewweb(\/|\\)/]
        },
        use: [{
            loader: 'babel-loader',
            options: {
                presets: ['env']
            }
        }]
    });
    return config;
};
