const path = require('path');
const { ModuleFederationPlugin } = require('webpack').container;

module.exports = {
    entry: './src/PromocodeButton.jsx',
    output: {
        path: path.resolve(__dirname, '../platzky_promocode/static'),
        publicPath: 'auto',
        clean: { keep: /remoteEntry|^\d+\.js/ },
    },
    plugins: [
        new ModuleFederationPlugin({
            name: 'promocode',
            filename: 'remoteEntry.js',
            exposes: {
                './Button': './src/PromocodeButton.jsx',
            },
            shared: {
                react: { singleton: true, requiredVersion: '^18.2.0' },
                'react-dom': { singleton: true, requiredVersion: '^18.2.0' },
            },
        }),
    ],
    module: {
        rules: [
            {
                test: /\.(js|jsx)$/,
                loader: 'babel-loader',
                exclude: /node_modules/,
            },
        ],
    },
    resolve: {
        extensions: ['.js', '.jsx'],
    },
};
