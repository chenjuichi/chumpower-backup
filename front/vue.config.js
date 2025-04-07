//const { defineConfig } = require('@vue/cli-service')
//module.exports = defineConfig({
//  transpileDependencies: true
//})

const { defineConfig } = require('@vue/cli-service')
const webpack = require('webpack');

module.exports = defineConfig({
  transpileDependencies: true,
  // 2024-06-08 add
  configureWebpack: {
    plugins: [
      new webpack.DefinePlugin({
        // Vue CLI is in maintenance mode, and probably won't merge my PR to fix this in their tooling
        // https://github.com/vuejs/vue-cli/pull/7443
        __VUE_PROD_HYDRATION_MISMATCH_DETAILS__: 'false',
        // 模擬 process 物件以防止 "process is not defined" 錯誤
        //'process.env': JSON.stringify(process.env),  // 傳遞 process.env 變數, 2025-03-31 add
      })
    ],
  },
  //
  devServer: {
    client: {
      overlay: {
        runtimeErrors: false,
      },
    },
  },
});